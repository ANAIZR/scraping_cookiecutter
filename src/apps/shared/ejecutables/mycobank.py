from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import hashlib
import os
from pymongo import MongoClient
import gridfs
from datetime import datetime
from bs4 import BeautifulSoup
import time

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

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

url = "https://www.mycobank.org/Simple%20names%20search"

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)

def handle_modal(driver, modal_link):
    try:
        WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(modal_link)
        ).click()
        print("Modal abierto.")
        
        WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.first-column"))
        )

        
        modal_soup = BeautifulSoup(driver.page_source, "html.parser")
        
        first_column = modal_soup.find("div", class_="first-column")
        modal_data = {}

        if first_column:
            rows = first_column.find_all("div", class_="row")
            for row in rows:
                row_data = row.get_text(strip=True)
                modal_data[row_data] = row_data
        
        print("Datos del modal extraidos:", modal_data)
        return modal_data

    except Exception as e:
        print("No se pudo abrir o leer el modal ", e)
        return None

def close_modal(driver):
    try:
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.header-action.action-close"))
        )
        close_button.click()
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.modal-content"))
        )
        print("Modal cerrado.")
    except Exception as e:
        print("No se pudo cerrar el modal ", e)

try:
    driver.get(url)
    print(f"Entrando a la página: {url}")
    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#search-btn"))
    ).click()
    print("Botón de búsqueda")
    time.sleep(5)

    all_scraped = []
    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, "table.mat-table tbody tr")
        print(f"Encontradas {len(rows)} filas en la página actual.") # por siaca el print

        for row in rows:
            try:
                modal_link = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a")
                modal_data = handle_modal(driver, modal_link)
                if modal_data:
                    all_scraped.append(modal_data)
                    close_modal(driver)
            except Exception as e:
                print("Error al manejar el enlace del modal ", e)

        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next']")
            if next_button.is_enabled():
                next_button.click()
                print("Siguiente pagina")
                time.sleep(5)
            else:
                print("No hay más páginas")
                break
        except Exception as e:
            print("Error al intentar avanzar al siguiente paginador", e)
            break

    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="scraped_data")
    with open(file_path, "w", encoding="utf-8") as file:
        for entry in all_scraped:
            file.write(str(entry) + "\n")
        file.flush() # por siacaso

    print(f"Contenido extraído: {all_scraped}")
    print(f"Archivo de salida: {file_path}")


finally:
    driver.quit()