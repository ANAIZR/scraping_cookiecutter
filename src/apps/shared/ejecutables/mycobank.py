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
import time
from bs4 import BeautifulSoup

# Directorio de salida para guardar los archivos
output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)


# Función para generar un directorio basado en la URL
def generate_directory(output_dir, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    folder_name = url.split("//")[-1].replace("/", "_") + "_" + url_hash[:8]
    folder_path = os.path.join(output_dir, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path


# Función para generar nombres de archivo versionados
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
        modal_link.click()
        print("Modal abierto.")

        WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div>div.first-column")
            )
        )
        print("Modal visible.")
        time.sleep(4)
        modal_soup = BeautifulSoup(driver.page_source, "html.parser")
        modal_content = modal_soup.get_text(strip=True)
        print("Contenido del modal extraído.")
        return modal_content  # Devolver solo el contenido del modal

    except Exception as e:
        print("No se pudo abrir o leer el modal.")
        print(e)
        return None


def close_modal(driver):
    try:
        close_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a.header-action.action-close")
            )
        )
        close_button.click()
        print("Modal cerrado.")

        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, "table.mat-table tbody")
            )
        )
        print("Modal cerrado y desaparecido.")

    except Exception as e:
        print("No se pudo cerrar el modal.")
        print(e)


all_scraped = ""

try:
    driver.get(url)
    print(f"Entrando a la página: {url}")
    print("Esperando a que cargue la página")

    boton = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#search-btn"))
    )
    driver.execute_script("arguments[0].scrollIntoView();", boton)
    WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#search-btn"))
    ).click()
    print("Botón clickeado")
    time.sleep(5)

    try:
        table_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.mat-table tbody"))
        )
        print("Tabla encontrada.")
    except Exception as e:
        print("No se encontró la tabla.")
        print(e)

    rows = driver.find_elements(By.CSS_SELECTOR, "table.mat-table tbody tr")
    print(f"Encontradas {len(rows)} filas")

    for row in rows:
        second_td = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
        if second_td:
            try:
                modal_link = second_td.find_element(
                    By.CSS_SELECTOR, "a[href='javascript:void(0)']"
                )
                print("Enlace con javascript:void(0) encontrado.")

                # Manejar el modal
                modal_content = handle_modal(driver, modal_link)

                if modal_content:
                    time.sleep(2)
                    all_scraped += modal_content + "\n\n"
                    close_modal(driver)

            except Exception as e:
                print(
                    "No se encontró el enlace o hubo un problema al interactuar con el modal."
                )
                print(e)

    # Guardar el contenido en un archivo
    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="scraped_data")

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(all_scraped)

    # Guardar el archivo en MongoDB
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

    # Eliminar versiones antiguas si hay más de 2 documentos para la misma URL
    docs_count = collection.count_documents({"Url": url})
    if docs_count > 2:
        docs_for_url = collection.find({"Url": url}).sort("Fecha_scrapper", -1)
        for doc in docs_for_url[2:]:
            collection.delete_one({"_id": doc["_id"]})
            fs.delete(doc["Objeto"])

    print(f"Datos guardados en MongoDB y archivo: {file_path}")

finally:
    driver.quit()

