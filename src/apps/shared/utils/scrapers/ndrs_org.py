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
import os
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status
import time
from selenium.webdriver.support.ui import Select


def scraper_ndrs_org(url, sobrenombre):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    output_dir = os.path.expanduser("~/")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    base_url = "https://www.ndrs.org.uk/"

    base_folder_path = generate_directory(output_dir, base_url)

    data_collected = []

    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        containers = soup.select("#MainContent .volumes .column")

        if not containers:
            driver.quit()

        for index, container in enumerate(containers):
            title = (
                container.select_one("h2").text.strip()
                if container.select_one("h2")
                else "No Title"
            )

            enlace = (
                container.select_one("a")["href"] if container.select_one("a") else None
            )
            if enlace:
                container_url = base_url + enlace

                driver.get(container_url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )

                time.sleep(3)

                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                article_list = page_soup.select("ul.clist li a")

                if not article_list:
                    continue

                for article in article_list:
                    article_title = article.text.strip()
                    article_url = article["href"]
                    article_full_url = base_url + article_url

                    folder_path = generate_directory(base_folder_path, article_full_url)

                    driver.get(article_full_url)
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                    )

                    article_soup = BeautifulSoup(driver.page_source, "html.parser")
                    article_title_text = (
                        article_soup.title.text if article_soup.title else "No Title"
                    )
                    body_text = article_soup.select_one("#repbody")

                    if article_title_text and body_text:
                        contenido = f"{body_text.text}"
                        file_path = get_next_versioned_filename(
                            folder_path, base_name=sobrenombre
                        )
                        with open(file_path, "w", encoding="utf-8") as file:
                            file.write(contenido)

                        with open(file_path, "rb") as file_data:
                            object_id = fs.put(
                                file_data,
                                filename=os.path.basename(file_path),
                            )
                            data = {
                                "Objeto": object_id,
                                "Tipo": "Web",
                                "Url": article_full_url,
                                "Fecha_scrapper": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "Etiquetas": ["planta", "plaga"],
                            }
                            collection = db["collection"]
                            collection.insert_one(data)
                            delete_old_documents(article_full_url, collection, fs)

                            data_collected.append(
                                {
                                    "Url": article_full_url,
                                    "Fecha_scrapper": data["Fecha_scrapper"],
                                    "Etiquetas": data["Etiquetas"],
                                }
                            )

                driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent"))
                )

                time.sleep(3)

                soup = BeautifulSoup(driver.page_source, "html.parser")
                containers = soup.select("#MainContent .volumes .column")

                if len(containers) <= index + 1:
                    break
                time.sleep(2)

    except Exception as e:
        print(f"Ocurrió un error: {e}")

    driver.quit()
    if data_collected:
        return Response(
            {
                "message": "Escrapeo realizado con éxito",
                "data": data_collected,
            },
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {"message": "No se generaron datos. Volver a realizar el scraping"},
            status=status.HTTP_400_BAD_REQUEST,
        )
