from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
import gridfs
import os
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time


def scraper_se_eppc(
    url,
    sobrenombre,
):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    all_scraper = ""
    try:
        driver.get(url)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.content1 table tbody")
            )
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tr_tags = soup.select("div.content1 table tbody tr")

        for index, tr in enumerate(tr_tags[1:], start=2):
            try:
                first_td = tr.select_one("td:first-child a")
                if first_td:
                    href = first_td.get("href")
                    driver.get(href)
                    time.sleep(5)
                    nav_fact_sheets = WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                "div.container ul.nav li:nth-child(1)",
                            )
                        )
                    )
                    nav_fact_sheets.click()
                    time.sleep(5)
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    content = soup.find("#overview")
                    if content:
                        all_scraped += content.text
                    else:
                        continue
            except Exception as e:
                import traceback

                traceback.print_exc()

        if all_scraper.strip():
            response_data = save_scraped_data(
                all_scraper, url, sobrenombre, collection, fs
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
