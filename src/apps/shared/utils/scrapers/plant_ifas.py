from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import os
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status
import random
from urllib.parse import urljoin

logger = get_logger("scraper")


def scraper_plant_ifas(url, sobrenombre):

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    try:
        driver.get(url)
        logger.info(f"Accediendo a {url}")
        time.sleep(2)

        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#app section.plant-cards"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        content = soup.select_one("#app section.plant-cards")

        if content:
            cards = content.select("ul.plants li.plant")
            logger.info(f"Se encontraron {len(cards)} tarjetas de plantas.")
            all_scraper += f"Se encontraron {len(cards)} tarjetas de plantas.\n"

            for i, card in enumerate(cards, start=1):
                link_card_element = card.select_one("a")
                if link_card_element:
                    link_card = link_card_element.get("href")
                    if link_card:
                        base_url = urljoin(url, link_card)
                        logger.info(f"Procesando tarjeta {i}: {base_url}")
                        all_scraper += f"Procesando tarjeta {i}: {base_url}\n"

                        driver.get(base_url)
                        time.sleep(random.uniform(3, 5)) 

                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "section.plant-page")
                            )
                        )

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        container = soup.select_one("div.content")
                        if container:
                            logger.info(f"Contenido extraído de {base_url}")
                            all_scraper += container.text.strip() + "\n"
                        else:
                            logger.warning(f"No se encontró contenido en {base_url}")
        else:
            logger.warning("No se encontró contenido en la sección de tarjetas de plantas.")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
