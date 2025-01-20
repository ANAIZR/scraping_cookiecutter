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
import time
import random

logger = get_logger("scraper","plant_ifas")


def scraper_plant_ifas(
    url,
    sobrenombre,
):

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    try:
        driver.get(url)
        wait_time = random.uniform(5, 15)
        time.sleep(2)
        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#app section.plant-cards")
            )
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        content = soup.select_one("#app section.plant-cards")
        if content:
            cards = content.select("ul.plants li.plant")
            all_scraper += f"Found {len(cards)} cards\n"
            for i, card in enumerate(cards, start=1):

                link_card_element = card.select_one("a")
                if link_card_element:
                    link_card = link_card_element.get("href")
                    if link_card:
                        base_url = f"{url+link_card}"
                        driver.get(base_url)
                        print(f"Url scrapeada {base_url}")
                        all_scraper += "Url scrapeada " + base_url + "\n"
                        WebDriverWait(driver, wait_time).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "section.plant-page")
                            )
                        )
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        conteiner = soup.select_one("div.content")
                        if conteiner:

                            all_scraper += conteiner.text + "\n"
            time.sleep(1)
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
