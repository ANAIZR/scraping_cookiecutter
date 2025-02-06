from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    initialize_driver,
    get_logger,
    generate_directory,
    get_next_versioned_filename,
    connect_to_mongo,
    delete_old_documents,
    load_keywords,
)
import os
import random
import time
from datetime import datetime
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
from selenium.common.exceptions import TimeoutException
from requests.exceptions import ConnectionError


def scraper_padil(url, sobrenombre):
    try:

        logger = get_logger("PADIL")
        logger.info(f"Iniciando scraping para URL: {url}")
        driver = initialize_driver()
        collection, fs = connect_to_mongo("scrapping-can", "collection")

        main_folder = generate_directory(sobrenombre)
        keywords = load_keywords("plants.txt")
        base_domain = "https://www.padil.gov.au"

        visited_urls = set()
        scraping_failed = False
    except Exception as e:
        logger.error(f"Error al inicializar el scraper: {str(e)}")

    try:
        driver.get(url)
        logger.info("Página de PADIL cargada exitosamente.")

        for keyword in keywords:
            logger.info(f"Procesando palabra clave: {keyword}")
            keyword_folder = generate_directory(keyword, main_folder)
            keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)
            content_accumulated = ""

            while True:
                try:
                    search_box = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                "div.main input.k-input-inner[placeholder='Search for anything']",
                            )
                        )
                    )
                    search_box.clear()
                    time.sleep(random.uniform(6, 10))
                    search_box.send_keys(keyword)
                    search_box.send_keys(Keys.RETURN)
                    logger.info(f"Palabra clave '{keyword}' buscada.")
                    time.sleep(random.uniform(6, 10))

                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.search-results")
                        )
                    )

                    results = driver.find_elements(
                        By.CSS_SELECTOR, "div.search-results div.search-result a"
                    )
                    result_count = len(results)
                    logger.info(
                        f"Se encontraron {result_count} resultados para '{keyword}'."
                    )

                    for result_index in range(result_count):
                        try:
                            driver.get(url)
                            logger.info(
                                "Volviendo a la página inicial para nueva búsqueda."
                            )

                            search_box = WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (
                                        By.CSS_SELECTOR,
                                        "div.main input.k-input-inner[placeholder='Search for anything']",
                                    )
                                )
                            )
                            search_box.clear()
                            time.sleep(random.uniform(6, 10))
                            search_box.send_keys(keyword)
                            search_box.send_keys(Keys.RETURN)
                            time.sleep(random.uniform(6, 10))

                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "div.search-results")
                                )
                            )
                            results = driver.find_elements(
                                By.CSS_SELECTOR,
                                "div.search-results div.search-result a",
                            )

                            if result_index >= len(results):
                                logger.warning(
                                    "El índice supera el número de resultados disponibles."
                                )
                                break

                            href = results[result_index].get_attribute("href")
                            if (
                                href
                                and href.startswith(base_domain)
                                and href not in visited_urls
                            ):
                                logger.info(f"Procesando enlace: {href}")
                                visited_urls.add(href)

                                driver.get(href)
                                WebDriverWait(driver, 60).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "body")
                                    )
                                )
                                time.sleep(random.uniform(6, 10))
                                soup = BeautifulSoup(driver.page_source, "html.parser")
                                pest_details = soup.find("div", class_="pest-details")

                                if pest_details:
                                    content_accumulated += f"URL: {href}\nTexto: {pest_details.text.strip()}\n\n"
                                else:
                                    logger.error(
                                        f"El elemento 'div.pest-details' no se encontró en {href}."
                                    )

                        except Exception as e:
                            logger.error(f"Error al procesar el enlace: {str(e)}")
                            scraping_failed = True
                            continue

                    logger.info(f"Procesamiento de '{keyword}' completado.")
                    driver.get(url)
                    break

                except Exception as e:
                    logger.error(f"Error durante la búsqueda de '{keyword}': {str(e)}")
                    scraping_failed = True
                    break
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

            return response_data
    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,            
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

                "Mensaje": "Ocurrió un error al procesar los datos.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
