from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import hashlib
from pymongo import MongoClient
import gridfs
from datetime import datetime

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

url = "https://www.ala.org.au/"
all_scraped = ""

try:
    driver.get(url)
    btn = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']"))
    )
    btn.click()
    time.sleep(2)

    while True:  # Bucle para iterar a través de las páginas
        # Esperar a que el OL esté disponible
        ol = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ol"))
        )

        # Extraer los elementos <li> de la página
        lis = driver.find_elements(By.CSS_SELECTOR, "ol li.search-result")
        print(f"Se encontraron {len(lis)} elementos <li> en la página actual.")

        for li in lis:
            try:
                a_tag = li.find_element(By.TAG_NAME, "a")
                href = a_tag.get_attribute("href")
                if href:
                    # Verifica si el enlace es relativo y crea la URL completa
                    if href.startswith('/'):
                        href = url + href[1:]

                    print(f"Haciendo clic en el enlace: {href}")

                    # Hacer clic en el enlace, esto navegará dentro de la misma ventana
                    a_tag.click()

                    # Esperar a que la página se haya cargado completamente
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "section.container-fluid"))
                    )

                    # Aquí puedes realizar acciones en la nueva página, como extraer información o procesarla
                    print("Nueva página cargada. Realizando acciones...")
                    content = driver.find_element(By.CSS_SELECTOR, "section.container-fluid")
                    all_scraped += content.text  # Asegúrate de que .text sea lo que deseas extraer

                    # Volver a la página principal (asegúrate de que no se cierre la ventana)
                    driver.back()

                    # Esperar un poco para que la página anterior se recargue completamente
                    time.sleep(2)

            except Exception as e:
                print(f"No se pudo hacer clic en el enlace o error al procesar el <li>: {e}")

        # Verificar si hay un enlace "Siguiente" para navegar a la siguiente página
        try:
            next_page_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")
            next_page_url = next_page_btn.get_attribute("href")
            if next_page_url:
                print(f"Haciendo clic en 'Siguiente' para cargar la siguiente página: {next_page_url}")
                driver.get(next_page_url)  # Navegar a la siguiente página
                time.sleep(3)  # Esperar que la siguiente página cargue
            else:
                print("No se encontró un enlace 'Siguiente'. Fin del scraping.")
                break  # No hay más páginas, terminamos el scraping
        except Exception as e:
            print("No se encontró un enlace 'Siguiente'. Fin del scraping.")
            break  # No hay más páginas, terminamos el scraping

    # Guardar los datos en MongoDB y en un archivo
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
