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

from selenium.webdriver.support.ui import Select


def scrape_ippc(url, sobrenombre):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    output_dir = r"C:\\web_scraping_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_scraped = ""

    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "select[name='publications_length']")
            )
        )

        select_element = driver.find_element(By.NAME, "publications_length")
        select = Select(select_element)
        select.select_by_value("-1")

        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#publications tr"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("#publications tr")
        if rows:
            print(f"Se encontraron {len(rows)} filas.")
            for row_index, row in enumerate(rows, start=1):

                tds = row.find_all("td")
                for td in tds:
                    link = td.find("a", href=True)
                    if link:
                        href = link["href"]

                        if href.startswith("/"):
                            href = f"https://www.ippc.int{href}"

                        driver.get(href)
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                        )

                        page_soup = BeautifulSoup(driver.page_source, "html.parser")
                        page_title = page_soup.select_one("#divmainbox > h1")
                        page_content = page_soup.select_one("dl.dl-horizontal")

                        if page_title:
                            all_scraped += page_title.get_text(strip=True) + "\n"
                        if page_content:
                            all_scraped += page_content.get_text(strip=True) + "\n\n"

                        driver.back()
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.container>div.row")
                            )
                        )

        if all_scraped.strip():
            folder_path = generate_directory(output_dir, url)
            file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(all_scraped)

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

            return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return Response(
            {"error": "Ocurrió un error durante el scraping."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
