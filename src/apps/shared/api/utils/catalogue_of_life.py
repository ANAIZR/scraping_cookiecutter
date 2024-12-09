from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
import os
from .functions import (
    save_scraped_data,
)
from rest_framework.response import Response
from rest_framework import status
import time


def scrape_catalogue_of_life(url, sobrenombre):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    all_scrapped = ""

    try:
        driver.get(url)
        print("Ingresando")
        input_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, "search_string"))
        )
        print("Escribiendo")
        input_field.send_keys("Acer")

        input_field.submit()

        time.sleep(4)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        table_with_trs = driver.find_element(By.XPATH, "(//table//table//table//table//table//table)[1]")
        trs_inside_table = table_with_trs.find_elements(By.XPATH, ".//tr")
        for tr in trs_inside_table:
            print(tr.text)

        if all_scrapped.strip():
                response_data = save_scraped_data(
                    all_scrapped, url, sobrenombre, collection, fs
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