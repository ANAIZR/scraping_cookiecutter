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
from .functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status
import time
import os
import hashlib
import requests
import pdfplumber
from io import BytesIO
import urllib3


def scrape_pdf_content_and_save(pdf_url, parent_folder, collection, fs):
    try:
        response = requests.get(pdf_url, stream=True, verify=False, timeout=10)
        response.raise_for_status()

        pdf_folder = generate_directory(parent_folder, hashlib.md5(pdf_url.encode()).hexdigest())
        pdf_buffer = BytesIO(response.content)

        with pdfplumber.open(pdf_buffer) as pdf:
            text_content = "\n".join(
                [f"--- Página {i + 1} ---\n{page.extract_text()}" for i, page in enumerate(pdf.pages)]
            )

        file_path = get_next_versioned_filename(pdf_folder, base_name="contenido_pdf")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(text_content)

        with open(file_path, "rb") as file_data:
            object_id = fs.put(file_data, filename=os.path.basename(file_path))

        data = {
            "Objeto": object_id,
            "Tipo": "PDF",
            "Url": pdf_url,
            "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["planta", "plaga"],
        }
        collection.insert_one(data)

        delete_old_documents(pdf_url, collection, fs)
        print(f"PDF guardado correctamente: {pdf_url}")

    except Exception as e:
        print(f"Error al guardar contenido PDF: {e}")


def scrape_all_pdfs_from_page(url, content_selector, attribute, attribute_second, output_dir, collection, fs):
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, content_selector)))
        table_content = driver.find_element(By.CSS_SELECTOR, content_selector)
        pdf_links = table_content.find_elements(By.CSS_SELECTOR, attribute)

        main_folder = generate_directory(output_dir, hashlib.md5(url.encode()).hexdigest())

        for link in pdf_links:
            pdf_url = link.get_attribute(attribute_second)
            scrape_pdf_content_and_save(pdf_url, main_folder, collection, fs)

    except Exception as e:
        print(f"Error durante el scraping: {e}")

    finally:
        driver.quit()


def scrape_ipm_illinoes(url, content_selector, attribute, attribute_second):
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        client = MongoClient("mongodb://localhost:27017/")
        db = client["scrapping-can"]
        collection = db["collection"]
        fs = gridfs.GridFS(db)

        output_dir = r"C:\web_scraping_files"
        os.makedirs(output_dir, exist_ok=True)

        scrape_all_pdfs_from_page(url, content_selector, attribute, attribute_second, output_dir, collection, fs)

        return {"message": "Scraping completado y datos guardados."}

    except Exception as e:
        return {"error": str(e)}