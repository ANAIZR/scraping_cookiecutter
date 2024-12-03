from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os
import hashlib
from pymongo import MongoClient
import gridfs
from datetime import datetime
import time

# Crear carpeta de salida
output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)


def generate_directory(output_dir, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    folder_name = url.split("//")[-1].replace("/", "_") + "_" + url_hash[:8]
    folder_path = os.path.join(output_dir, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path


def get_next_versioned_filename(folder_path, base_name="archivo"):
    version = 0
    while True:
        file_name = f"{base_name}_v{version}.txt"
        file_path = os.path.join(folder_path, file_name)
        if not os.path.exists(file_path):
            return file_path
        version += 1


# Configuración del navegador
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Conexión a MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

url = "https://plants.usda.gov/"
all_scraped = ""

try:
    driver.get(url)
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#main-content"))
    )
    characteristic = driver.find_element(
        By.CSS_SELECTOR, "div.sidebar-desktop li:first-child a"
    )
    characteristic.click()

    time.sleep(2)

    try:

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "section.content table tbody tr")
            )
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tr_tags = soup.select("section.content table tbody tr")
        print(f"Se encontraron {len(tr_tags)}")
        time.sleep(2)
        for index, tr in enumerate(tr_tags[1:], start=2):
            try:
                print(f"Procesando fila {index}")
                if tr.select("td"):
                    link_tag = tr.select_one("td:nth-child(2) a")
                    if link_tag:
                        href = link_tag.get("href")
                        print(f"Fila {index}: Enlace encontrado: {href}")
                        if href.startswith("/"):
                            href = f"https://plants.usda.gov{href}"
                            print(f"Accediendo a la página: {href}")
                            driver.get(href)
                            WebDriverWait(driver, 20).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "body")
                                )
                            )

                            page_soup = BeautifulSoup(driver.page_source, "html.parser")
                            page_title = page_soup.h1 if page_soup.h1 else "Sin título"
                            print(f"Título de la página: {page_title}")
                    else:
                        print(
                            f"Fila {index}: No se encontró el enlace en la segunda celda."
                        )
                else:
                    print(
                        f"Fila {index}: La fila no contiene celdas (es probable que sea un encabezado)."
                    )
            except Exception as e:
                print(f"Error en la fila {index}: {e}")
                import traceback

                traceback.print_exc()

    except Exception as e:
        print(f"error {e}")
finally:
    driver.quit()
