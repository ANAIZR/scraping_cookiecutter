from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import gridfs
import os
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time


def scraper_nematode(
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
        while True:
            content = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.view"))
            )

            rows = driver.find_elements(By.CSS_SELECTOR, "div.views-row")

            for row in rows:
                fields = row.find_elements(
                    By.CSS_SELECTOR, "div.content div.field--label-inline"
                )
                for field in fields:
                    label = field.find_element(
                        By.CSS_SELECTOR, "div.field--label"
                    ).text.strip()

                    field_items = []

                    spans = field.find_elements(By.CSS_SELECTOR, "span")
                    for span in spans:
                        text = span.text.strip()
                        if text and text not in field_items:
                            field_items.append(text)

                    divs = field.find_elements(By.CSS_SELECTOR, "div.field--item")
                    for div in divs:
                        text = div.text.strip()
                        if text and text not in field_items:
                            field_items.append(text)

                    field_text = " ".join(field_items).strip()

                    all_scraper += f"{label}: {field_text}\n"
                all_scraper += "\n"
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a[title='Go to next page']")
                    )
                )
                next_button_class = next_button.get_attribute("class")
                if "disabled" in next_button_class or "is-active" in next_button_class:
                    break
                else:
                    next_button.click()
                    WebDriverWait(driver, 10).until(EC.staleness_of(content))
            except Exception as e:
                break
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
