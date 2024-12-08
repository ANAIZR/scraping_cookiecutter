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
from .functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status
import time


def scrape_ala_org(
    url,
    sobrenombre,
):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    output_dir = r"C:\web_scraping_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_scrapped = ""
    try:
        driver.get(url)
        btn = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']"))
        )
        btn.click()
        time.sleep(2)

        while True:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ol"))
            )

            lis = driver.find_elements(By.CSS_SELECTOR, "ol li.search-result")

            for li in lis:
                try:
                    a_tag = li.find_element(By.CSS_SELECTOR, "a")
                    href = a_tag.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            href = url + href[1:]

                        a_tag.click()

                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "section.container-fluid")
                            )
                        )

                        content = driver.find_element(
                            By.CSS_SELECTOR, "section.container-fluid"
                        )
                        all_scrapped += content.text

                        driver.back()

                        time.sleep(2)

                except Exception as e:
                    print(
                        f"No se pudo hacer clic en el enlace o error al procesar el <li>: {e}"
                    )

            try:
                next_page_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")
                next_page_url = next_page_btn.get_attribute("href")
                if next_page_url:
                    driver.get(next_page_url)
                    time.sleep(3)
                else:
                    break
            except Exception as e:
                break

        folder_path = generate_directory(output_dir, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(all_scrapped)

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
    finally:
        driver.quit()
