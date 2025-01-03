from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import time

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
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    keywords = load_keywords()
    all_scraper = ""  # Variable para almacenar todos los datos extraídos
    processed_links = set()  # Set para almacenar los enlaces ya procesados

    try:
        driver.get(url)
        logger.info("Página de PADIL cargada exitosamente.")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.main"))
        )

        for keyword in keywords:
            try:
                # Buscar la barra de búsqueda y realizar la búsqueda inicial
                search_box = WebDriverWait(driver, 50).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "div.main input.k-input-inner[placeholder='Search for anything']",
                        )
                    )
                )

                if not search_box:
                    logger.error("No se pudo localizar la barra de búsqueda.")
                    continue

                random_wait()
                search_box.clear()
                search_box.send_keys(keyword)
                search_box.send_keys(Keys.RETURN)
                logger.info(f"Palabra clave '{keyword}' buscada en la barra.")

                # Esperar a que se carguen los resultados
                WebDriverWait(driver, 50).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.search-results")
                    )
                )
                time.sleep(2)
                logger.info(f"Resultados cargados para: {keyword}")

                # Variable para controlar si aún hay resultados

                try:
                    # Extraer resultados y navegar a cada enlace
                    content_result = driver.find_elements(
                        By.CSS_SELECTOR, "div.search-results div.search-result div.name"
                    )

                    print(f"Elementos encontrados {len(content_result)}")

                    for result in content_result:
                        print(f"Elemento ---> {result.text.strip()}")

                except Exception as e:
                    logger.error(f"Error al extraer los resultados: {str(e)}")
                    

            except Exception as e:
                logger.error(f"Error durante la búsqueda de {keyword}: {str(e)}")
                continue

        # Procesar los datos y almacenarlos en MongoDB
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()


def random_wait(min_wait=2, max_wait=6):
    wait_time = random.uniform(min_wait, max_wait)
    logger.info(f"Esperando {wait_time:.2f} segundos...")
    time.sleep(wait_time)
