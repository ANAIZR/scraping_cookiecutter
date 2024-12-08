from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
from datetime import datetime
import gridfs
import os
from .functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time


def scrape_iucnredlist(url, sobrenombre):
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
    visited_urls = set()
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#redlist-js"))
        )
        btn = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search--site__button"))
        )
        btn.click()

        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.cards--narrow article")
            )
        )

        while True:
            articles = driver.find_elements(
                By.CSS_SELECTOR, "div.cards--narrow article a"
            )

            for index, article in enumerate(articles):
                href = article.get_attribute("href")

                if href in visited_urls:
                    continue

                driver.get(href)

                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                try:
                    # Inicializar variables
                    title = ""
                    taxonomy = ""
                    habitat = ""
                    try:
                        title = WebDriverWait(driver, 30).until(
                            lambda d: d.find_element(
                                By.CSS_SELECTOR,
                                "h1.headline__title",
                            ).text.strip()
                        )
                    except Exception as e:
                        print(f"Error al obtener el título: {e}")
                    try:
                        taxonomy = WebDriverWait(driver, 30).until(
                            lambda d: d.find_element(
                                By.CSS_SELECTOR, "#taxonomy"
                            ).text.strip()
                        )
                    except Exception as e:
                        print(f"Error al obtener la taxonomia: {e}")
                    try:
                        habitat = WebDriverWait(driver, 30).until(
                            lambda d: d.find_element(
                                By.CSS_SELECTOR, "#habitat-ecology"
                            ).text.strip()
                        )
                    except Exception as e:
                        print(f"Error al obtener el hábitat: {e}")

                    text_content = title + taxonomy + habitat
                    if title:
                        all_scrapped += text_content
                except Exception as e:
                    print(f"Error procesando el artículo: {e}")
                visited_urls.add(href)
                time.sleep(5)
                driver.back()
                print("Regresando a la página principal...")

            try:
                show_more_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".section__link-out"))
                )
                show_more_btn.click()

                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div.cards--narrow article")
                    )
                )
            except Exception as e:
                print("No se encontró el botón 'Show more' o no se pudo hacer clic.")
                break

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
