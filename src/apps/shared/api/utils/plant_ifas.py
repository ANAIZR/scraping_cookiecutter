from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import gridfs
import time
import os
from .functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status


def scrape_plant_ifas(
    url,
    sobrenombre,
):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scrapped = ""
    try:
        driver.get(url)
        time.sleep(5)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#app section.plant-cards")
            )
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        content = soup.select_one("#app section.plant-cards")
        if content:
            cards = content.select("ul.plants li.plant")

            for i, card in enumerate(cards, start=1):
                link_card_element = card.select_one("a")
                if link_card_element:
                    link_card = link_card_element.get("href")
                    if link_card:
                        base_url = f"{url+link_card}"
                        driver.get(base_url)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "section.plant-page")
                            )
                        )
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        conteiner = soup.select_one("div.content")
                        if conteiner:
                            primary_content = conteiner.select(
                                "div.primary div[style*='margin:2rem']"
                            )
                            second_content = conteiner.select(
                                "div.primary div[style*='margin-bottom:2rem']"
                            )
                            all_content = "\n".join(
                                [
                                    element.get_text(strip=True)
                                    for element in primary_content + second_content
                                ]
                            )
                            all_scrapped += all_content

            time.sleep(1)
        output_dir = r"C:\web_scraping_files"
        if all_scrapped.strip():
            response_data = save_scraped_data(
                all_scrapped, url, sobrenombre, output_dir, collection, fs
            )
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos para scrapear.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )

    except Exception as e:
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
