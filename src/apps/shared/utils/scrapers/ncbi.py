from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from selenium.common.exceptions import  TimeoutException
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
                ul_compact = driver.find_element(By.XPATH, "//ul[@compact]")
                first_li = ul_compact.find_element(By.TAG_NAME, "li")
                first_a = first_li.find_element(By.TAG_NAME, "a")
                detail_url = first_a.get_attribute("href")
                if detail_url:
                    logger.info(f"Accediendo al enlace de detalle: {detail_url}")
                    driver.get(detail_url)

                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                    # Extraer datos a partir del tercer <table>
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    tables = soup.find_all("table")

                    if len(tables) >= 3:
                        third_table = tables[2]
                        table_text = third_table.get_text(separator="\n", strip=True)
                        content_accumulated += f"{detail_url}\n{table_text}\n\n"

            except Exception as e:
                logger.warning(f"No se encontró <ul compact>, saltando al siguiente término. Error: {e}")
                continue  
            if content_accumulated:
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

