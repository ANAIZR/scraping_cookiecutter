from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
    process_scraper_data,
    save_to_mongo
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
from bson import ObjectId


def scraper_padil(url, sobrenombre):
    try:

        logger = get_logger("PADIL")
        logger.info(f"Iniciando scraping para URL: {url}")
        driver = initialize_driver()
        collection, fs = connect_to_mongo()
        total_scraped_links = 0
        scraped_urls = []
        non_scraped_urls = []
        keywords = load_keywords("plants.txt")
        if not keywords:
            return Response(
                {
                    "status": "error",
                    "message": "El archivo de palabras clave está vacío o no se pudo cargar.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        base_domain = "https://www.padil.gov.au"

        visited_urls = set()
    except Exception as e:
        logger.error(f"Error al inicializar el scraper: {str(e)}")

    try:
        driver.get(url)
        logger.info("Página de PADIL cargada exitosamente.")

        for keyword in keywords:
            logger.info(f"Procesando palabra clave: {keyword}")
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
                                    content_accumulated = f"{pest_details.text.strip()}\n\n"
                                    if content_accumulated:
                                        object_id = save_to_mongo("urls_scraper", content_accumulated, href, url)  # 📌 Guardar en `urls_scraper`
                                        total_scraped_links += 1
                                        scraped_urls.append(url)
                                        logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")

                                        
                                else:
                                    logger.error(
                                        f"El elemento 'div.pest-details' no se encontró en {href}."
                                    )
                            else:
                                non_scraped_urls.append(href)



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


        all_scraper = (
            f"Total enlaces scrapeados: {total_scraped_links}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )  
        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
        
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
