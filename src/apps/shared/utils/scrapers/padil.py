from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    initialize_driver,
    get_logger,
    generate_directory,
    get_next_versioned_filename,
)
import os
import random
import time
import requests
from bs4 import BeautifulSoup

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


def scraper_padil(url,sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    output_dir = "c:/web_scraper_files"
    main_folder = generate_directory(output_dir, "padil_scraper")
    keywords = load_keywords()
    all_links = []  # Lista para almacenar todos los enlaces encontrados

    try:
        driver.get(url)
        logger.info("Página de PADIL cargada exitosamente.")

        for keyword in keywords:
            try:
                # Buscar la barra de búsqueda
                search_box = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "div.main input.k-input-inner[placeholder='Search for anything']",
                        )
                    )
                )
                search_box.clear()
                search_box.send_keys(keyword)
                search_box.send_keys(Keys.RETURN)
                logger.info(f"Palabra clave '{keyword}' buscada.")
                time.sleep(2)  # Breve pausa para asegurar la carga

                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.search-results")
                    )
                )
                time.sleep(2)  # Breve pausa para asegurar la carga

                # Extraer los hrefs
                results = driver.find_elements(
                    By.CSS_SELECTOR, "div.search-results div.search-result a"
                )
                keyword_folder = generate_directory(main_folder, keyword)
                keyword_links = []

                for result in results:
                    href = result.get_attribute("href")
                    if href and href.startswith("/"):
                        absolute_href = f"https://www.padil.gov.au{href}"
                        keyword_links.append(absolute_href)

                logger.info(
                    f"Se encontraron {len(keyword_links)} enlaces para '{keyword}'."
                )
                all_links.extend(keyword_links)

                # Regresar a la página principal
                driver.get(url)
                time.sleep(2)

            except Exception as e:
                logger.error(f"Error durante la búsqueda de '{keyword}': {str(e)}")
                continue

        logger.info("Búsquedas con Selenium completadas. Cerrando navegador.")
    except Exception as e:
        logger.error(f"Error durante el scraping con Selenium: {str(e)}")
    finally:
        driver.quit()

    # Usar requests para procesar los enlaces
    logger.info("Iniciando extracción de contenido con requests.")
    for href in all_links:
        try:
            response = requests.get(href, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            pest_details = soup.find("div", class_="pest-details")

            if pest_details:
                link_folder = generate_directory(keyword_folder, "details")
                file_path = get_next_versioned_filename(link_folder, "pest_details")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(pest_details.text.strip())
                logger.info(f"Datos guardados en: {file_path}")

        except Exception as e:
            logger.error(f"Error al procesar {href}: {str(e)}")

    logger.info("Scraping completado exitosamente.")


def random_wait(min_wait=2, max_wait=6):
    wait_time = random.uniform(min_wait, max_wait)
    logger.info(f"Esperando {wait_time:.2f} segundos...")
    time.sleep(wait_time)
