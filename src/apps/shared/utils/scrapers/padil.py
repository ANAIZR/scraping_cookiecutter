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
)
import os
import random
import time
import requests
import datetime
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("scraper")


def load_keywords(file_path="../txt/all.txt"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(base_path, file_path)
        with open(absolute_path, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]
        logger.info(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        logger.error(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise


def scraper_padil(url, sobrenombre):
    try:

        logger.info(f"Iniciando scraping para URL: {url}")
        driver = initialize_driver()
        collection, fs = connect_to_mongo("scrapping-can", "collection")

        main_folder = generate_directory(url)
        keywords = load_keywords()
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
                                    contenido = f"{pest_details.text.strip()}\n\n\n"
                                    link_folder = generate_directory(
                                        href, keyword_folder
                                    )
                                    file_path = get_next_versioned_filename(
                                        link_folder, keyword
                                    )
                                    with open(file_path, "w", encoding="utf-8") as file:
                                        file.write(contenido)

                                    with open(file_path, "rb") as file_data:
                                        object_id = fs.put(
                                            file_data,
                                            filename=os.path.basename(file_path),
                                        )
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
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            collection.insert_one(data)
            delete_old_documents(url, collection, fs)
            response = Response(data, status=status.HTTP_200_OK)
            return response
    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return {"status": "error", "message": f"Error durante el scraping: {str(e)}"}

    finally:
        driver.quit()
