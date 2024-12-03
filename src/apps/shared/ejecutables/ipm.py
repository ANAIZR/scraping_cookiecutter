import os
import hashlib
import requests
import pdfplumber
from io import BytesIO
from datetime import datetime
from pymongo import MongoClient
import gridfs
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import urllib3

# Desactivar advertencias de seguridad
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración de directorios
output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def generate_directory(output_dir, *path_segments):
    """
    Genera una estructura de directorios basada en segmentos de ruta.
    """
    folder_path = os.path.join(output_dir, *path_segments)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def get_next_versioned_filename(folder_path, base_name="archivo"):
    """
    Obtiene un nombre de archivo versionado único.
    """
    version = 0
    while True:
        file_name = f"{base_name}_v{version}.txt"
        file_path = os.path.join(folder_path, file_name)
        if not os.path.exists(file_path):
            return file_path
        version += 1

# Configuración de MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

def scrape_pdf_content_and_save(pdf_url, parent_folder):
    try:
        # Descargar el contenido del PDF
        response = requests.get(pdf_url, stream=True, verify=False)
        response.raise_for_status()

        # Crear subcarpeta específica para el PDF
        pdf_folder = generate_directory(parent_folder, hashlib.md5(pdf_url.encode()).hexdigest())
        
        # Leer el contenido en un buffer de memoria
        pdf_buffer = BytesIO(response.content)

        # Procesar el PDF con pdfplumber
        with pdfplumber.open(pdf_buffer) as pdf:
            text_content = ""
            for i, page in enumerate(pdf.pages):
                text_content += f"\n--- Página {i + 1} ---\n{page.extract_text()}\n"

            # Guardar el contenido en un archivo versionado
            file_path = get_next_versioned_filename(pdf_folder, base_name="contenido_pdf")
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(text_content)

            # Guardar el archivo en MongoDB
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

                # Limitar a 2 documentos por URL
                docs_count = collection.count_documents({"Url": pdf_url})
                if docs_count > 2:
                    docs_for_url = collection.find({"Url": pdf_url}).sort("Fecha_scrapper", -1)
                    for doc in docs_for_url[2:]:
                        collection.delete_one({"_id": doc["_id"]})
                        fs.delete(doc["Objeto"])

            print(f"Procesado y guardado: {file_path}, ObjectId: {object_id}")

    except Exception as e:
        print(f"Error al procesar el PDF ({pdf_url}): {e}")

def scrape_all_pdfs_from_page(url):
    # Crear subcarpeta para la URL principal
    main_folder = generate_directory(output_dir, hashlib.md5(url.encode()).hexdigest())

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table:nth-child(3)"))
        )
        table_content = driver.find_element(By.CSS_SELECTOR, "table:nth-child(3)")
        pdf_links = table_content.find_elements(By.CSS_SELECTOR, "a[href$='.pdf']")

        for link in pdf_links:
            pdf_url = link.get_attribute("href")
            print(f"\nProcesando PDF: {pdf_url}")
            scrape_pdf_content_and_save(pdf_url, main_folder)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

# URL principal
page_url = "https://ipm.illinois.edu/diseases/index.html"
scrape_all_pdfs_from_page(page_url)
