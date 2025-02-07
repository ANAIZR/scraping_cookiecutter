from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
)
from rest_framework.response import Response
from rest_framework import status
import os

def scraper_ncbi(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    keywords = load_keywords("viruses.txt")
    main_folder = generate_directory(sobrenombre)
    object_id = None
    scraping_failed = False
    response_data_list = []

    if not keywords:
        logger.error("El archivo de palabras clave está vacío o no se pudo cargar.")
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
            content_accumulated = ""

            search_box = driver.find_element(By.ID, "searchtxt")
            search_box.clear()
            search_box.send_keys(keyword)
            search_box.submit()

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            try:
                keyword_folder = generate_directory(keyword, main_folder)
                keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)

                try:
                    form_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "form"))
                    )
                    ul_compact = form_element.find_element(By.XPATH, ".//ul[@compact]")
                    links = ul_compact.find_elements(By.TAG_NAME, "a")

                except (TimeoutException, NoSuchElementException):
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    form = soup.find("form")
                    if form:
                        tables = form.find_all("table", {"width": "100%"})
                        if tables:
                            table_text = "\n".join(
                                table.get_text(separator="\n", strip=True) for table in tables
                            )
                            if table_text.strip():
                                content_accumulated += f"Término: {keyword}\n{table_text}\n\n"
                                logger.info(f"Texto extraído directamente de la tabla en la búsqueda de {keyword}")
                    continue  

                for index in range(len(links)):
                    try:
                        form_element = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.TAG_NAME, "form"))
                        )
                        ul_compact = form_element.find_element(By.XPATH, ".//ul[@compact]")
                        links = ul_compact.find_elements(By.TAG_NAME, "a")

                        href = links[index].get_attribute("href")
                        if href and href.startswith("https://www.ncbi.nlm.nih.gov/"):
                            logger.info(f"Accediendo al enlace: {href}")
                            driver.get(href)

                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )

                            soup = BeautifulSoup(driver.page_source, "html.parser")
                            form = soup.find("form")

                            if form:
                                tables = form.find_all("table", {"width": "100%"})
                                if tables:
                                    table_text = "\n".join(
                                        table.get_text(separator="\n", strip=True) for table in tables
                                    )
                                    if table_text.strip():
                                        content_accumulated += f"URL: {href}\n{table_text}\n\n"
                                        logger.info(f"Texto extraído del enlace: {href}")
                            driver.back()

                    except StaleElementReferenceException:
                        logger.warning(f"Elemento obsoleto en {href}, reintentando...")
                        break
                    except Exception as e:
                        logger.warning(f"Error al procesar el enlace {href}: {e}")
                        continue

                if content_accumulated.strip():
                    logger.info(f"Guardando contenido acumulado para la palabra clave: {keyword}")
                    with open(keyword_file_path, "w", encoding="utf-8") as keyword_file:
                        keyword_file.write(content_accumulated)

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
                        "Mensaje": f"Datos de '{keyword}' han sido scrapeados correctamente.",
                    }
                    collection.insert_one(data)
                    delete_old_documents(url, collection, fs)

            except Exception as e:
                logger.warning(f"No se encontró `<ul compact>` para la palabra clave: {keyword}. Error: {e}")
                continue

        logger.info("Scraping completado con éxito.")

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
