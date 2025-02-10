from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    get_next_versioned_pdf_filename,
    process_scraper_data,
    load_keywords
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

logger = get_logger("scraper")

def scraper_canada_ca(url, sobrenombre):
    driver = initialize_driver()
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 6))
        logger.info(f"Iniciando scraping para URL: {url}")

        collection, fs = connect_to_mongo()
        main_folder = generate_directory(sobrenombre)

        keywords = load_keywords("plants.txt")
        if not keywords:
            return Response(
                {
                    "status": "error",
                    "message": "El archivo de palabras clave está vacío o no se pudo cargar.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Página de canada.ca cargada exitosamente.")

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")

            try:
                driver.get(url)
                time.sleep(random.uniform(3, 6))

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#sch-inp-ac"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                
                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button#sch-inp"))
                )
                search_button.click()
                time.sleep(random.uniform(3, 6))
            except Exception as e:
                logger.error(f"Error al buscar la palabra clave: {keyword}. Error: {str(e)}")
                continue

            keyword_folder = generate_directory(keyword, main_folder)
            keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)

            content_accumulated = ""
            hrefs = set() 
            total_urls_found = 0

            max_first_result = 20

            while True:
                try:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")

                    links = soup.select("section#wb-land a[href]")

                    if not links:
                        logger.warning(f"No se encontraron enlaces en la búsqueda para '{keyword}'")
                        break

                    for link in links:
                        full_href = link.get("href")
                        if full_href and full_href.startswith("http"):
                            hrefs.add(full_href)
                            total_urls_found += 1

                    current_url = driver.current_url

                    if "firstResult=" in current_url:
                        first_result_value = int(current_url.split("firstResult=")[1].split("&")[0])
                    else:
                        first_result_value = 0

                    if first_result_value >= max_first_result:
                        logger.info(f"Se alcanzó el límite de paginación (firstResult={max_first_result}). Deteniendo el scraping.")
                        break

                    try:
                        time.sleep(2)

                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.page-button.next-page-button"))
                        )

                        driver.execute_script("arguments[0].click();", next_button)

                        logger.info(f"Se hizo clic en el botón 'Next'. Nueva URL: {driver.current_url}")

                        time.sleep(random.uniform(3, 6))

                    except (TimeoutException, NoSuchElementException):
                        logger.info("No hay más páginas disponibles o no se encontró el botón 'Next'.")
                        break

                except Exception as e:
                    logger.error(f"Error al obtener los resultados de la búsqueda: {str(e)}")
                    break
            
            for href in hrefs:
                try:
                    driver.get(href)
                    time.sleep(random.uniform(3, 6))

                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")

                    main_content = soup.select_one("main.main-container")
                    if main_content:
                        text_content = main_content.get_text(strip=True)
                    else:
                        text_content = "No se encontró contenido"

                    content_accumulated += f"URL: {href}\nContenido:\n{text_content}\n\n"
                    content_accumulated += "-" * 100 + "\n\n"

                except Exception as e:
                    logger.error(f"Error al extraer contenido de {href}: {str(e)}")
                    continue

            if content_accumulated:
                try:
                    with open(keyword_file_path, "w", encoding="utf-8") as keyword_file:
                        keyword_file.write(content_accumulated)

                    with open(keyword_file_path, "rb") as file_data:
                        object_id = fs.put(
                            file_data,
                            filename=os.path.basename(keyword_file_path),
                            metadata={
                                "url": url,
                                "keyword": keyword,
                                "content": content_accumulated,
                                "scraping_date": datetime.now(),
                                "Etiquetas": ["planta", "plaga"],
                            },
                        )
                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                    existing_versions = list(
                        collection.find({
                            "metadata.keyword": keyword,
                            "metadata.url": url  
                        }).sort("metadata.scraping_date", -1)
                    )
                    logger.info(f"Versiones encontradas para '{keyword}': {existing_versions}")

                    try:
                        if len(existing_versions) > 2:
                            oldest_version = existing_versions[-1]  
                            fs.delete(oldest_version["_id"])  
                            collection.delete_one({"_id": oldest_version["_id"]}) 
                            logger.info(
                                f"Se eliminó la versión más antigua de '{keyword}' con URL '{url}' y object_id: {oldest_version['_id']}'"
                            )
                    except Exception as e:
                        logger.error(f"Error al eliminar versiones antiguas: {str(e)}")

                    data = {
                        "Objeto": object_id,
                        "Tipo": "Web",
                        "Url": url,
                        "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Etiquetas": ["planta", "plaga"],
                    }

                    collection.insert_one(data)
                    delete_old_documents(url, collection, fs)

                    return Response(
                        {
                            "Tipo": "Web",
                            "Url": url,
                            "Mensaje": f"Se encontraron {total_urls_found} URLs y se guardaron correctamente.",
                        },
                        status=status.HTTP_200_OK,
                    )

                except Exception as e:
                    logger.error(f"Error al guardar los datos en MongoDB: {str(e)}")

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
                "Mensaje": f"Ocurrió un error al procesar los datos: {str(e)}",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        if driver:
            driver.quit()
            logger.info("Navegador cerrado")
