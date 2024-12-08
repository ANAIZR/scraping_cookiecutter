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


def scrape_pnw_hand_books(
    url,
    sobrenombre
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

        def scrape_current_page():
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div.view-content div.views-row")
                    )
                )
                containers = driver.find_elements(
                    By.CSS_SELECTOR, "div.view-content div.views-row"
                )

                for container in containers:
                    link = container.find_element(
                        By.CSS_SELECTOR, "div.views-field-title a"
                    )
                    href = link.get_attribute("href")

                    driver.get(href)
                    time.sleep(2)
                    soup = BeautifulSoup(driver.page_source, "html.parser")

                    title = soup.find("h1")

                    driver.back()
                    time.sleep(2)

            except Exception as e:
                print(f"Error al procesar la página actual: {e}")

        def go_to_next_page():
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "li.next a")
                next_button.click()
                time.sleep(3)
                return True
            except Exception as e:
                print("No se encontró el botón 'Next'. Fin de la paginación.")
                return False

        try:
            time.sleep(5)
            boton = driver.find_element(
                By.CSS_SELECTOR, "#edit-submit-plant-subarticles-autocomplete"
            )
            boton.click()
            time.sleep(3)

            while True:
                scrape_current_page()

                if not go_to_next_page():
                    break

        except Exception as e:
            print(f"Error durante el proceso de scraping: {e}")
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
