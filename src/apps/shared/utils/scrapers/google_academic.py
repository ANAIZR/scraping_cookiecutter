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


# Cargar palabras clave desde utils/txt/plants.txt
def load_keywords(file_path="../txt/plants.txt"):
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


import random
import time


def scraper_google_academic(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    keywords = load_keywords()  # Cargar palabras clave desde plants.txt
    results = {}

    try:
        driver.get(url)
        logger.info("Página de Google Académico cargada exitosamente.")

        # Localizar la barra de búsqueda en Google Académico
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        logger.info("Barra de búsqueda localizada.")

        # Iterar por cada palabra clave y realizar la búsqueda
        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")

            # Introducir un tiempo de espera aleatorio antes de interactuar con el buscador
            random_wait()

            # Ingresar la palabra clave y presionar Enter
            search_box.clear()
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)

            # Esperar a que se carguen los resultados
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "gs_res_ccl_mid"))
            )
            logger.info(f"Resultados cargados para: {keyword}")

            # Obtener todos los enlaces de los resultados de la primera página
            result_links = driver.find_elements(By.CSS_SELECTOR, "h3 a")
            links = [
                link.get_attribute("href")
                for link in result_links
                if link.get_attribute("href")
            ]

            logger.info(f"Enlaces encontrados para {keyword}: {links}")

            # Crear una lista para almacenar los contenidos de cada enlace
            content_by_keyword = []

            for link in links:
                logger.info(f"Ingresando al enlace: {link}")
                driver.get(link)  # Navegar al enlace

                try:
                    # Introducir un tiempo de espera aleatorio antes de extraer contenido
                    random_wait()

                    # Esperar hasta que el contenido principal esté cargado
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    logger.info("Contenido de la página cargado.")

                    # Extraer todo el contenido visible de la página
                    page_content = driver.find_element(By.TAG_NAME, "body").text
                    content_by_keyword.append({"url": link, "content": page_content})

                except Exception as e:
                    logger.error(
                        f"Error al extraer contenido del enlace {link}: {str(e)}"
                    )

                finally:
                    logger.info(f"Regresando a la página de resultados...")
                    driver.back()  # Regresar a la página de resultados

                    # Introducir un tiempo de espera aleatorio antes de continuar con el siguiente enlace
                    random_wait()

            # Guardar el contenido en el diccionario de resultados
            results[keyword] = content_by_keyword

        # Procesar los datos y almacenarlos en MongoDB
        response = process_scraper_data(results, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()


# Función auxiliar para introducir un tiempo de espera aleatorio
def random_wait(min_wait=2, max_wait=6):
    wait_time = random.uniform(min_wait, max_wait)
    logger.info(f"Esperando {wait_time:.2f} segundos...")
    time.sleep(wait_time)
