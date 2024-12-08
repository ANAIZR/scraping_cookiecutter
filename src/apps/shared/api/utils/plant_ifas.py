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
from .functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
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
    all_scrapper=""
    try:
        driver.get(url)
        time.sleep(5)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#app section.plant-cards"))
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
                            primary_content = conteiner.select("div.primary div[style*='margin:2rem']")
                            second_content = conteiner.select("div.primary div[style*='margin-bottom:2rem']")
                            all_content = "\n".join(
                                [
                                    element.get_text(strip=True)
                                    for element in primary_content + second_content
                                ]
                            )
                            all_scrapper += all_content
            
            time.sleep(1)
        output_dir = r"C:\web_scraping_files"
        folder_path = generate_directory(output_dir, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(all_scrapper)

        with open(file_path, "rb") as file_data:
            object_id = fs.put(file_data, filename=os.path.basename(file_path))

            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            response_data = {
                    "Tipo": "Web",
                    "Url": url,
                    "Fecha_scrapper": data["Fecha_scrapper"],
                    "Etiquetas": data["Etiquetas"],
                    "Mensaje": "Los datos han sido scrapeados correctamente.",

                }
            collection.insert_one(data)
            delete_old_documents(url, collection, fs)
        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
