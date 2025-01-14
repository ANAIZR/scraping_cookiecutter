from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import time
import os
import random
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory
)
from selenium.common.exceptions import StaleElementReferenceException

logger = get_logger("scraper")

def load_keywords(file_path="../txt/plants.txt"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(base_path, file_path)
        with open(absolute_path, "r", encoding="utf-8") as f:
            keywords = [
                line.strip() for line in f if isinstance(line, str) and line.strip()
            ]
        logger.info(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        logger.info(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise

def scraper_herbarium(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#wrapper")
            )
        )

        link_list = driver.find_elements(
            By.CSS_SELECTOR, "#nav ul li a"
        )

        main_folder = generate_directory(url)

    
        while True:
            if not link_list:
                break
            new_links_found = False
            for link in link_list:
                href = link.get_attribute("href")

                if href in processed_links:
                    continue

                processed_links.add(href)
                new_links_found = True

                try:
                    driver.get(href)

                    original_window = driver.current_window_handle

                    keywords = load_keywords()
                    visited_urls = set()
                    scraping_failed = False


                    for keyword in keywords:
                        print(f"Buscando con la palabra clave: {keyword}")
                        keyword_folder = generate_directory(keyword, main_folder)
                        try:
                            search_input =  WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='species']"))
                                )
                            search_input.clear()
                            search_input.send_keys(keyword)
                            time.sleep(random.uniform(3, 6))

                            search_input.submit()

                            #######################PAGINA A SCRAPEAR#######################

                            driver.execute_script("window.open(arguments[0]);", href)

                            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

                            new_window = driver.window_handles[1]
                            driver.switch_to.window(new_window)

                            driver.switch_to.window(original_window)

                            logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
                            time.sleep(random.uniform(3, 6))
                            # driver.back()
                        except Exception as e:
                            logger.info(f"Error al realizar la búsqueda: {e}")
                            scraping_failed = True
                            continue

                #     WebDriverWait(driver, 60).until(
                #         EC.presence_of_element_located(
                #             (By.CSS_SELECTOR, "div.c-wysiwyg")
                #         )
                #     )

                #     page_soup = BeautifulSoup(driver.page_source, "html.parser")
                #     content_div = page_soup.find("div", class_="c-wysiwyg")
                #     time.sleep(5)
                except:
                    print("Error en el contenido")

    except Exception as e:
        print(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        try:
            driver.quit()
        except Exception as e:
            print(f"Error al cerrar el navegador: {e}")