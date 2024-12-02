from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
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


def scrape_iucnredlist(
    url,
    selector,
    search_button_selector,
    content_selector,
    content_selector_second,
    attribute,
    tag_name_first,
    tag_name_second,
    tag_name_third,
    tag_name_fourth,
    search_button_selector_second,
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

    output_dir = r"C:\web_scraping_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_scrapped = ""
    visited_urls = set()  # Conjunto para almacenar enlaces ya visitados
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        btn = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, search_button_selector))
        )
        btn.click()

        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, content_selector))
        )

        while True:
            articles = driver.find_elements(By.CSS_SELECTOR, content_selector_second)

            for index, article in enumerate(articles):
                href = article.get_attribute(attribute)

                if href in visited_urls:
                    continue

                driver.get(href)

                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, tag_name_first))
                )

                try:
                    title = WebDriverWait(driver, 30).until(
                        lambda d: d.find_element(
                            By.CSS_SELECTOR, tag_name_second
                        ).text.strip()
                    )
                except Exception as e:
                    print(f"Error al obtener el título: {e}")
                try:
                    taxonomy = WebDriverWait(driver, 30).until(
                        lambda d: d.find_element(
                            By.CSS_SELECTOR, tag_name_third
                        ).text.strip()
                    )
                except Exception as e:
                    print(f"Error al obtener la taxonomia: {e}")
                try:
                    habitat = WebDriverWait(driver, 30).until(
                        lambda d: d.find_element(
                            By.CSS_SELECTOR, tag_name_fourth
                        ).text.strip()
                    )
                except Exception as e:
                    print(f"Error al obtener el hábitat: {e}")

                text_content = title + taxonomy + habitat
                if title:
                    all_scrapped += text_content

                visited_urls.add(href)

                driver.back()
                print("Regresando a la página principal...")

            try:
                show_more_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, search_button_selector_second)
                    )
                )
                show_more_btn.click()
                
                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, content_selector)
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

        collection.insert_one(data)

        delete_old_documents(url, collection, fs)

        print(f"Los datos se han guardado en MongoDB y en el archivo: {file_path}")
        return Response(
            {"message": "Scraping completado y datos guardados en MongoDB."},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
