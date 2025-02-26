from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from rest_framework.response import Response
from rest_framework import status
import time
import random
from ..functions import (
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
non_scraped_urls = []  
scraped_urls = []

def load_search_terms(file_path):
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except Exception as e:
        print(f"Error al cargar términos: {e}")
        return []


def scraper_index_fungorum(url, sobrenombre):
    search_terms = load_search_terms(
        os.path.join(os.path.dirname(__file__), "../txt/plants.txt")
    )

    if not search_terms:
        return Response(
            {"error": "No se encontraron términos para buscar."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    try:
        driver.get(url)

        for term in search_terms:
            try:

                input_field = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "SearchTerm"))
                )
                input_field.clear()
                input_field.send_keys(term)
                input_field.submit()
                time.sleep(random.uniform(3, 6))
                logger.info(f"Realizando búsqueda con la palabra clave: {term}")

                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mainbody"))
                )
                time.sleep(random.uniform(3, 6))
                logger.info("Búsqueda realizada con éxito")

                links = driver.find_elements(By.CSS_SELECTOR, "a.LinkColour1")

                if not links:
                    continue

                for index, link in enumerate(links, start=1):
                    href = link.get_attribute("href")
                    text = link.text.strip()

                    driver.get(href)
                    main = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "table.mainbody")
                        )
                    )

                    try:
                        content = main.text
                        all_scraper += content
                    except Exception as e:
                        pass

                    driver.back()
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "table.mainbody")
                        )
                    )  

                input_field = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "SearchTerm"))
                )
                input_field.clear()  

            except Exception as e:
                pass


        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response


    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
