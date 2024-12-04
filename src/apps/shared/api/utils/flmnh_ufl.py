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

def scrape_flmnh_ufl(
    url,
    selector,
    content_selector,
    tag_name_first,
    content_selector_second,
    sobrenombre
):
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")
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
    def scrape_page():
        # Esperar a que las filas de la tabla se carguen
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))

        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select(content_selector)


        all_scraped_data = []
        for row in rows:
            cols = row.find_all(tag_name_first)
            data = [col.text.strip() for col in cols]
            all_scraped_data.append(data)

    def go_to_next_page():
        try:
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "button-1065-btnEl")))

            next_button = driver.find_element(By.ID, "button-1065-btnEl")
            next_button.click()
            return True
        except Exception as e:
            return False    
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, content_selector_second)))
        btn = driver.find_element(By.CSS_SELECTOR, content_selector_second)
        btn.click()  
        
        scrape_page()

        while go_to_next_page():
            time.sleep(2)  
            scrape_page()

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