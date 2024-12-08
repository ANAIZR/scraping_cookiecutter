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
from .functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time


def scrape_eppo(
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


    all_scrapped = ""
    try:
        driver.get(url)
        time.sleep(2)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#dttable tbody tr"))
        )
        while True:
            rows = driver.find_elements(By.CSS_SELECTOR, "#dttable tbody tr")

            for i in range(len(rows)):
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, "#dttable tbody tr")
                    row = rows[i]

                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 1:
                        second_td = cells[1]
                        a_tag = second_td.find_element(By.TAG_NAME, "a")
                        href = a_tag.get_attribute("href")

                        if href:
                            driver.get(href)

                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (
                                        By.CSS_SELECTOR,
                                        "div.row>div.col-md-12>div.row>div.col-md-9",
                                    )
                                )
                            )
                            time.sleep(5)
                            page_source = driver.page_source
                            soup = BeautifulSoup(page_source, "html.parser")

                            content = soup.select_one(
                                "div.row>div.col-md-12>div.row>div.col-md-9"
                            )
                            if content:
                                all_scrapped += content.get_text() + "\n"

                            time.sleep(5)
                            driver.back()

                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "#dttable tbody tr")
                                )
                            )
                            print("Volviendo a la tabla, esperando recarga...")
                        else:
                            print("No se encontró un enlace en esta celda.")
                    else:
                        print("Fila no tiene suficientes celdas.")
                except Exception as e:
                    print(f"Error al procesar la fila o hacer clic en el enlace: {e}")
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

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
