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

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

url = "https://gd.eppo.int/datasheets/"
all_scraped = ""

try:
    driver.get(url)
    time.sleep(2)

    # Espera a que la tabla esté completamente cargada
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#dttable tbody tr"))
    )

    # Proceso iterativo
    while True:
        rows = driver.find_elements(By.CSS_SELECTOR, "#dttable tbody tr")
        print(f"Encontré {len(rows)} filas.")

        for i in range(len(rows)):
            try:
                # Volver a obtener las filas cada vez que regresamos
                rows = driver.find_elements(By.CSS_SELECTOR, "#dttable tbody tr")
                row = rows[i]

                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) > 1:  # Validar que la fila tenga al menos 2 celdas
                    second_td = cells[1]
                    a_tag = second_td.find_element(By.TAG_NAME, "a")
                    href = a_tag.get_attribute("href")

                    if href:
                        print(f"Haciendo clic en el enlace: {href}")
                        driver.get(href)

                        # Esperar a que la página destino esté cargada
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.row>div.col-md-12>div.row>div.col-md-9")
                            )
                        )
                        time.sleep(5)
                        page_source = driver.page_source
                        soup = BeautifulSoup(page_source, "html.parser")

                        content = soup.select_one("div.row>div.col-md-12>div.row>div.col-md-9")
                        if content:
                            print(content.get_text())
                            all_scraped += content.get_text() + "\n"

                        time.sleep(5)
                        driver.back()

                        # Esperar la recarga de la tabla
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "#dttable tbody tr"))
                        )
                        print("Volviendo a la tabla, esperando recarga...")
                    else:
                        print("No se encontró un enlace en esta celda.")
                else:
                    print("Fila no tiene suficientes celdas.")
            except Exception as e:
                print(f"Error al procesar la fila o hacer clic en el enlace: {e}")
        break

    # Guardar datos en un archivo local
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
    docs_count = collection.count_documents({"Url": url})
    if docs_count > 2:
        docs_for_url = collection.find({"Url": url}).sort("Fecha_scrapper", -1)
        for doc in docs_for_url[2:]:
            collection.delete_one({"_id": doc["_id"]})
            fs.delete(doc["Objeto"])

    print(f"Datos guardados en MongoDB y archivo: {file_path}")
finally:
    driver.quit()
