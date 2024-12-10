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


def scrape_pest_alerts(
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
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        original_window = driver.current_window_handle

        for row in rows:
            try:
                second_td = row.find_elements(By.TAG_NAME, "td")[1]
                a_tag = second_td.find_element(By.TAG_NAME, "a")
                href = a_tag.get_attribute("href")
                if href:
                    if href.startswith("/"):
                        href = url + href[1:]
                    driver.execute_script("window.open(arguments[0]);", href)

                    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

                    new_window = driver.window_handles[1]
                    driver.switch_to.window(new_window)

                    WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "div.bg-content-custom")
                        )
                    )

                    content_elements = driver.find_elements(
                        By.CSS_SELECTOR, "div.bg-content-custom"
                    )
                    if len(content_elements) == 2:
                        content = (
                            content_elements[0].text + "\n" + content_elements[1].text
                        )
                        all_scrapped += content

                    driver.close()

                    driver.switch_to.window(original_window)

                    time.sleep(2)

            except Exception as e:
                print(f"Error al procesar la fila o hacer clic en el enlace: {e}")
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
