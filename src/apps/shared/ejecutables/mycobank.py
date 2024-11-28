from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
import hashlib
import os
from pymongo import MongoClient
import gridfs
from datetime import datetime
import time
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


# Conexión a MongoDB y GridFS
client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

# URL a scrapear
url = "https://www.mycobank.org/Simple%20names%20search"

# Inicialización del driver de Selenium

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Variable para guardar el contenido raspado
all_scraped = ""

try:
    driver.get(url)
    print(f"Entrando a la página: {url}")
    print("Esperando a que cargue la página")
    print("Buscando elementos")
    boton = WebDriverWait(driver, 40).until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "#search-btn")
        )
    )
    print("Elemento encontrado")
    time.sleep(2)  
    driver.execute_script("arguments[0].click();", boton)
    print("Botón clickeado")
    time.sleep(5)
    print("Esperando a que cargue el cuerpo")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.ps-content table.mat-table tbody")
        )
    )
    soup = BeautifulSoup(driver.page_source, "html.parser")
    content = soup.select_one("div.ps-content table.mat-table tbody")
    print("Cuerpo cargado")
    if content:
        print("Cargando filas")
        rows = content.select("tr")

        print(f"Encontradas {len(rows)} filas")
        for row in rows:
            second_td = row.select_one("td:nth-child(2)")
            if second_td:
                td_a = second_td.select_one("a")
                if td_a and td_a.get("href"):
                    link = td_a.get("href")
                    print(f"Encontrado enlace: {link}")
                    
                    # Opcional: Si deseas navegar a este enlace, descomenta lo siguiente
                    # print(f"Entrando a la página: {link}")
                    # driver.get(link)
                    # time.sleep(5)  # Espera adicional para la nueva página

                else:
                    print("No se encontró un enlace válido en esta fila.")
            else:
                print("No se encontró la segunda celda en esta fila.")

                        

                """
                    modal_html = driver.page_source
                modal_soup = BeautifulSoup(modal_html, "html.parser")
                modal_content = modal_soup.select_one("div.field-container > div.w-100")
                if modal_content:
                    all_scraped += modal_content.get_text(strip=True) + "\n"

                close_modal = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.dockmodal-header > a.action-close"))
                )
                close_modal.click()
                    """       
                
                
    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="anscy")

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(all_scraped)

    # Guardar en MongoDB
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

    docs_count = collection.count_documents({"Url": url})
    if docs_count > 2:
        docs_for_url = collection.find({"Url": url}).sort("Fecha_scrapper", -1)
        for doc in docs_for_url[2:]:
            collection.delete_one({"_id": doc["_id"]})
            fs.delete(doc["Objeto"])

    print(f"Datos guardados en MongoDB y archivo: {file_path}")
finally:
    driver.quit()
