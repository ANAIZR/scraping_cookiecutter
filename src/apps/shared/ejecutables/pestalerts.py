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

url = "https://www.pestalerts.org/nappo/emerging-pest-alerts/"
all_scraped = ""

try:
    driver.get(url)
    table = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
    )

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    original_window = driver.current_window_handle

    for row in rows:
        try:
            second_td = row.find_elements(By.TAG_NAME, "td")
            a_tag = second_td.find_element(By.TAG_NAME, "a")
            href = a_tag.get_attribute("href")
            if href:
                if href.startswith("/"):
                    href = url + href[1:]

                print(f"Haciendo clic en el enlace: {href}")

                driver.execute_script("window.open(arguments[0]);", href)

                WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

                new_window = driver.window_handles[1]
                driver.switch_to.window(new_window)

                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.bg-content-custom"))
                )

                # Verifica que se han encontrado exactamente dos elementos
                content_elements = driver.find_elements(By.CSS_SELECTOR, "div.bg-content-custom")
                if len(content_elements) == 2:
                    content = content_elements[0].text + "\n" + content_elements[1].text  # Concatenar los textos
                    all_scraped += content  
                else:
                    print(f"Se esperaba encontrar exactamente 2 elementos, pero se encontraron {len(content_elements)}.")

                driver.close()

                driver.switch_to.window(original_window)

                time.sleep(2)

        except Exception as e:
            print(f"Error al procesar la fila o hacer clic en el enlace: {e}")

    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="scraped_data")

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(all_scraped)

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