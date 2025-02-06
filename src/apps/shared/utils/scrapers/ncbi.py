from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords
)
from bs4 import BeautifulSoup
from datetime import datetime


def scraper_ncbi(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    keywords = load_keywords("plants.txt")
    main_folder = generate_directory(sobrenombre)
    scraping_failed = False
    all_scraper = ""

    if not keywords:
        return Response(
            {
                "status": "error",
                "message": "El archivo de palabras clave está vacío o no se pudo cargar.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        for keyword in keywords:
            logger.info(f"Buscando término: {keyword}")
            search_box = driver.find_element(By.ID, "searchtxt")
            search_box.clear()
            search_box.send_keys(keyword)
            search_box.submit()

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            try:
                keyword_folder = generate_directory(keyword, main_folder)
                keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)

                try:
                    ul_compact = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//ul[@compact]"))
                    )
                    links = ul_compact.find_elements(By.TAG_NAME, "a")
                except (TimeoutException, NoSuchElementException):
                    logger.warning(f"No se encontró `<ul compact>` para la palabra clave: {keyword}")
                    
                    # Captura un screenshot y guarda el HTML para depuración
                    screenshot_path = os.path.join(keyword_folder, f"{keyword}_error.png")
                    html_path = os.path.join(keyword_folder, f"{keyword}_error.html")
                    driver.save_screenshot(screenshot_path)
                    with open(html_path, "w", encoding="utf-8") as file:
                        file.write(driver.page_source)

                    logger.info(f"Captura de pantalla guardada en {screenshot_path}")
                    logger.info(f"HTML guardado en {html_path}")

                    continue  # Pasar a la siguiente palabra clave

                for link in links:
                    detail_url = link.get_attribute("href")

                    if detail_url and detail_url.startswith("https://www.ncbi.nlm.nih.gov/"):
                        logger.info(f"Accediendo al enlace de detalle: {detail_url}")
                        driver.get(detail_url)

                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        form = soup.find("form")

                        if form:
                            tables = form.find_all("table")
                            if len(tables) >= 4:
                                fourth_table = tables[3]
                                table_text = fourth_table.get_text(separator="\n", strip=True)

                                references = [
                                    a.get("href") for a in fourth_table.find_all("a", href=True)
                                ]
                                ref_text = "\nReferencias:\n" + "\n".join(references) if references else ""

                                all_scraper += f"URL: {detail_url}\n{table_text}{ref_text}\n\n"

            except Exception as e:
                logger.warning(f"Error al procesar la palabra clave {keyword}. Detalles: {e}")
                continue  

            if all_scraper:
                with open(keyword_file_path, "w", encoding="utf-8") as keyword_file:
                    keyword_file.write(all_scraper)

                with open(keyword_file_path, "rb") as file_data:
                    object_id = fs.put(
                        file_data,
                        filename=os.path.basename(keyword_file_path),
                        metadata={
                            "keyword": keyword,
                            "scraping_date": datetime.now(),
                        },
                    )
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

        if scraping_failed:
            return Response(
                {
                    "message": "Error durante el scraping. Algunas URLs fallaron.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            response_data = {
                "Tipo": "Web",
                "Url": url,
                "Fecha_scraper": data["Fecha_scraper"],
                "Etiquetas": data["Etiquetas"],
                "Mensaje": "Los datos han sido scrapeados correctamente.",
            }

            collection.insert_one(data)
            delete_old_documents(url, collection, fs)

            return Response(
                {
                    "data": response_data,
                },
                status=status.HTTP_200_OK,
            )
    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "La página está tardando demasiado en responder. Verifique si la URL es correcta o intente nuevamente más tarde.",
            },
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )
    except ConnectionError:
        logger.error("Error de conexión a la URL.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "No se pudo conectar a la página web.",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        logger.error(f"Error al procesar datos del scraper: {str(e)}")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "Ocurrió un error al procesar los datos.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
        logger.info("Navegador cerrado")
