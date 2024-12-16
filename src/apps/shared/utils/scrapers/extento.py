from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time
from selenium.common.exceptions import TimeoutException, WebDriverException


def scraper_extento(url, sobrenombre):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
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

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
        )

        tables = driver.find_elements(By.TAG_NAME, "table")
        if len(tables) >= 2:
            second_table = tables[1]
            rows = second_table.find_elements(By.TAG_NAME, "tr")

            if len(rows) >= 2:
                second_row = rows[1]
                tds = second_row.find_elements(By.TAG_NAME, "td")

                first_level_links = [
                    link.get_attribute("href")
                    for td in tds
                    for link in td.find_elements(By.TAG_NAME, "a")
                    if link.get_attribute("href")
                ]

                for href in first_level_links:
                    driver.get(href)

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
                    )

                    new_tables = driver.find_elements(By.TAG_NAME, "table")
                    if len(new_tables) >= 3:
                        third_table = new_tables[2]
                        new_rows = third_table.find_elements(By.TAG_NAME, "tr")

                        second_level_links = [
                            new_link.get_attribute("href")
                            for new_row in new_rows
                            for new_td in new_row.find_elements(By.TAG_NAME, "td")
                            for new_link in new_td.find_elements(By.TAG_NAME, "a")
                            if new_link.get_attribute("href")
                        ]
                        if second_level_links:
                            for new_href in second_level_links:
                                driver.get(new_href)
                                try:
                                    body = WebDriverWait(driver, 30).until(
                                        EC.presence_of_element_located(
                                            (By.TAG_NAME, "body")
                                        )
                                    )
                                    if body:
                                        body_content = body.text
                                        if body_content.strip():
                                            all_scraper += body_content
                                            all_scraper += "\n\n"

                                    time.sleep(2)
                                finally:
                                    try:
                                        driver.back()
                                        WebDriverWait(driver, 10).until(
                                            EC.presence_of_all_elements_located(
                                                (By.TAG_NAME, "table")
                                            )
                                        )
                                    except WebDriverException as e:
                                        print(
                                            f"Error al regresar a la página anterior: {e}"
                                        )
                    try:
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
                        )
                    except WebDriverException as e:
                        print(f"Error al intentar volver a la página anterior: {e}")

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
