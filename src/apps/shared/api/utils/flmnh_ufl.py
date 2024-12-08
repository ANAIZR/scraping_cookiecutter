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
from .functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time


def scrape_flmnh_ufl(
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

    def scrape_page():
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "table.x-grid-table tbody tr")
            )
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("table.x-grid-table tbody tr:not(.x-grid-header-row)")

        all_scraped_data = []
        for row in rows:
            cols = row.find_all("td")
            data = [col.text.strip() for col in cols]
            all_scraped_data.append(data)

    def go_to_next_page():
        try:
            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "button-1065-btnEl"))
            )

            next_button = driver.find_element(By.ID, "button-1065-btnEl")
            next_button.click()
            return True
        except Exception as e:
            return False

    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl"))
        )
        btn = driver.find_element(By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl")
        btn.click()

        scrape_page()

        while go_to_next_page():
            time.sleep(2)
            scrape_page()

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
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
