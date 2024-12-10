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


def scrape_ala_org(
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
    finally:
        driver.quit()
