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
from bs4 import BeautifulSoup

logger = get_logger("scraper","catalogue_of_life")


# Cargar palabras clave desde utils/txt/all.txt
def load_keywords(file_path="../txt/all.txt"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(base_path, file_path)
        with open(absolute_path, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]
        # logger.info(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        logger.error(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise


def scraper_catalogue_of_life(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    keywords = load_keywords()
    all_scraper = ""

    try:
        driver.get(url)
        logger.info("Página cargada exitosamente.")

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "search_string"))
        )
        logger.info("Barra de búsqueda localizada.")

        for index, keyword in enumerate(keywords):
            logger.info(f"Buscando la palabra clave: {keyword}")
            all_scraper += f"Palabra clave {index + 1}: {keyword}\n"
            random_wait()

            search_box.clear()
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )
            logger.info(f"Resultados cargados para: {keyword}")

            rows = driver.find_elements(By.XPATH, "//tr[starts-with(@id, 'record_')]")
            for index in range(len(rows)):
                rows = driver.find_elements(
                    By.XPATH, "//tr[starts-with(@id, 'record_')]"
                )
                row = rows[index]
                record_id = row.get_attribute("id")
                logger.info(f"Procesando fila con id: {record_id}")

                try:
                    next_row = row.find_element(By.XPATH, "following-sibling::tr")
                    first_td = next_row.find_element(By.TAG_NAME, "td")
                    link = first_td.find_element(By.TAG_NAME, "a")
                    if link and link.get_attribute("href"):
                        href = link.get_attribute("href")
                        logger.info(f"Accediendo al enlace: {href}")
                        driver.get(href)
                        all_scraper += f"Link: {href}\n"
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                        )

                        page_content = BeautifulSoup(driver.page_source, "html.parser")
                        td_element = page_content.select(
                            'div table:nth-child(1) tr:nth-child(1) td:nth-child(3)[valign="top"]'
                        )
                        if td_element:
                            cleaned_text = " ".join(td_element[0].get_text().split())
                            all_scraper += cleaned_text + "\n"
                        else:
                            logger.warning(
                                f"No se encontró el tercer <td> para el enlace {href}"
                            )
                        all_scraper += "\n\n******************\n\n"
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                        )

                        random_wait()

                except Exception as e:
                    logger.error(
                        f"Error procesando el enlace en la fila con id {record_id}: {str(e)}"
                    )

            # Regresar a la página principal después de procesar todas las filas
            driver.get(url)
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "search_string"))
            )
            logger.info("Barra de búsqueda localizada.")

            logger.info(
                f"Palabra clave {keyword} procesada. Regresando a la página principal."
            )

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
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
