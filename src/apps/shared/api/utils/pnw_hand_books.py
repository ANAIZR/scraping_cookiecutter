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


def scrape_pnw_hand_books(
    url, selector, content_selector, attribute, tag_name_first, tag_name_second,search_button_selector,sobrenombre
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

    try:
        driver.get(url)
        def scrape_current_page():
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                containers = driver.find_elements(By.CSS_SELECTOR, selector)

                for container in containers:
                    link = container.find_element(By.CSS_SELECTOR, content_selector)
                    href = link.get_attribute(attribute)

                    driver.get(href)
                    time.sleep(2)
                    soup = BeautifulSoup(driver.page_source, "html.parser")

                    title = soup.find(tag_name_first)

                    driver.back()
                    time.sleep(2)

            except Exception as e:
                print(f"Error al procesar la página actual: {e}")

        def go_to_next_page():
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, tag_name_second)
                next_button.click()
                time.sleep(3)
                return True
            except Exception as e:
                print("No se encontró el botón 'Next'. Fin de la paginación.")
                return False

        try:
            time.sleep(5)
            boton = driver.find_element(By.CSS_SELECTOR, search_button_selector)
            boton.click()
            time.sleep(3)

            while True:
                scrape_current_page()

                if not go_to_next_page():
                    break

        except Exception as e:
            print(f"Error durante el proceso de scraping: {e}")
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

        return Response(
            {"message": "Scraping completado y datos guardados en MongoDB."},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
