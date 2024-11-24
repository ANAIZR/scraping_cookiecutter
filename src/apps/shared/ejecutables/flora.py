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

# Directorio de salida donde se guardarán los archivos
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


# Función para obtener el siguiente nombre de archivo versionado
def get_next_versioned_filename(folder_path, base_name="archivo"):
    version = 0
    while True:
        file_name = f"{base_name}_v{version}.txt"
        file_path = os.path.join(folder_path, file_name)
        if not os.path.exists(file_path):
            return file_path
        version += 1


# Conexión a la base de datos MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

url = "http://flora.huh.harvard.edu/china/"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
all_scrapped = ""

try:
    driver.get(url)

    search_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "body table tr:nth-child(2) td:nth-child(2) font p:nth-child(4) a",
            )
        )
    )
    search_button.click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "ul",
            )
        )
    )
    body_table = driver.find_element(By.CSS_SELECTOR, "ul")
    li_tags = body_table.find_elements(By.TAG_NAME, "li")

    for i, li_tag in enumerate(li_tags):
        try:
            a_tags = li_tag.find_elements(By.TAG_NAME, "a")
            print(f"Fila {i} tiene {len(a_tags)} enlaces.")

            if a_tags:
                first_a_tag = a_tags[0]
                href = first_a_tag.get_attribute("href")
                text = first_a_tag.text
                print(f"Enlace: {href}, Texto: {text}")

                if href.endswith(".pdf"):
                    continue

                driver.get(href)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#tdContent ")
                    )
                )

                try:
                    td_content = driver.find_element(By.CSS_SELECTOR, "#tdContent ")
                    if td_content:
                        all_scrapped += td_content.text + "\n"
                    else:
                        print(f"No se encontró el contenido en la página: {href}")
                        continue  # Continuar con la siguiente página

                except Exception as e:
                    print(f"No se encontró el contenido en la página: {href}, Error: {e}")
                    continue  # Continuar con la siguiente página

            driver.back()

        except Exception as e:
                print(f"Error procesando la fila {i}: {e}")


    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="flora")

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

    docs_count = collection.count_documents({"Url": url})
    if docs_count > 2:
        docs_for_url = collection.find({"Url": url}).sort("Fecha_scrapper", -1)
        for doc in docs_for_url[2:]:
            collection.delete_one({"_id": doc["_id"]})
            fs.delete(doc["Objeto"])

    print(f"Los datos se han guardado en MongoDB y en el archivo: {file_path}")

except Exception as e:
    print(f"Ocurrió un error: {e}")
finally:
    driver.quit()
