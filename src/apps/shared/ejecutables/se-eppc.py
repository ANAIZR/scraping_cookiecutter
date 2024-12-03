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

url = "https://www.se-eppc.org/weeds.cfm"
all_scraped = ""

try:
    driver.get(url)

    # Esperar la tabla principal
    table = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.content1 table tbody"))
    )
    soup = BeautifulSoup(driver.page_source, "html.parser")
    # Obtener las filas de la tabla
    tr_tags = soup.select("div.content1 table tbody tr")
    print(f"Se encontraron {len(tr_tags)} filas.")

    for index, tr in enumerate(tr_tags[1:], start=2):
        try:
            first_td = tr.select_one("td:first-child a")
            print(first_td)
            if first_td:
                href = first_td.get("href")
                print(f"Fila {index}: Enlace encontrado: {href}")
                driver.get(href)
                time.sleep(5)
                nav_fact_sheets = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        'div.container ul.nav li:nth-child(1)',
                        )
                    )
                )
                nav_fact_sheets.click()
                time.sleep(5)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                content = soup.find("#overview")
                if(content):
                    all_scraped += content.text
                else:
                    continue
                
            
            else:
                print(f"Fila {index}: No se encontró enlace en esta fila.")
        except Exception as e:
            print(f"Error en la fila {index}: {e}")
            import traceback
            traceback.print_exc()

    # Guardar datos en archivo
    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="scraped_data")

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(all_scraped)

    # Guardar el archivo en MongoDB usando GridFS
    with open(file_path, "rb") as file_data:
        object_id = fs.put(file_data, filename=os.path.basename(file_path))

    # Insertar información en la base de datos
    data = {
        "Objeto": object_id,
        "Tipo": "Web",
        "Url": url,
        "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Etiquetas": ["planta", "plaga"],
    }
    collection.insert_one(data)

    # Eliminar documentos antiguos si hay más de 2
    docs_for_url = list(collection.find({"Url": url}).sort("Fecha_scrapper", -1))
    for doc in docs_for_url[2:]:
        if fs.exists(doc["Objeto"]):
            fs.delete(doc["Objeto"])
        collection.delete_one({"_id": doc["_id"]})

    print(f"Datos guardados en MongoDB y archivo: {file_path}")
finally:
    driver.quit()