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
from .functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
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

        folder_path = generate_directory(output_dir, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(all_scrapped)

        with open(file_path, "rb") as file_data:
            object_id = fs.put(file_data, filename=os.path.basename(file_path))

            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            response_data = {
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": data["Fecha_scrapper"],
                "Etiquetas": data["Etiquetas"],
                "Mensaje": "Los datos han sido scrapeados correctamente.",
            }

            collection.insert_one(data)

            delete_old_documents(url, collection, fs)

        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
