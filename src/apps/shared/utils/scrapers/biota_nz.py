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


def scraper_biota_nz(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    keywords = load_keywords()  
    results = {}

    try:
        driver.get(url)
        logger.info("Página de BIOTA NZ cargada exitosamente.")

        # Localizar la barra de búsqueda en Google Académico
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#query"))
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

            # Esperar a que se carguen los resultados
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "list-result"))
            )
            logger.info(f"Resultados cargados para: {keyword}")

            # Obtener todos los enlaces de los resultados
            links = driver.find_elements(By.CSS_SELECTOR, "div.row-separation div.col-12.a")

            # Iterar por cada enlace
            for link in links:
                href = link.get_attribute("href")
                text = link.text.strip()
                if href:
                    logger.info(f"Accediendo al enlace: {href}")

                    # Hacer clic en el enlace para ir a la página de detalles
                    driver.get(href)

                    # Esperar a que se cargue el contenido de la página de detalles
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.page-content-wrapper"))  # Ajusta el selector
                    )

                    # Realizar el scraping de la página de detalles
                    page_content = driver.page_source

                    # Aquí puedes procesar el contenido de la página como desees
                    results[text] = page_content

                    # Regresar a la página de resultados
                    driver.back()

                    # Esperar un poco antes de continuar con el siguiente enlace
                    random_wait()

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
