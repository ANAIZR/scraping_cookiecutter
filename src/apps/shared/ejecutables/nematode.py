from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
import os
import hashlib
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
url = "https://nematode.ars.usda.gov/"
driver.get(url)
print(f"Entrando a la página: {url}")

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

all_scrapped = ""

try:
    while True:
        content = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.view"))
        )

        rows = driver.find_elements(By.CSS_SELECTOR, "div.views-row")

        for row in rows:
            fields = row.find_elements(By.CSS_SELECTOR, "div.content div.field--label-inline")
            for field in fields:
                label = field.find_element(By.CSS_SELECTOR, "div.field--label").text.strip()
                
                field_items = []

                spans = field.find_elements(By.CSS_SELECTOR, "span")
                for span in spans:
                    text = span.text.strip()
                    if text and text not in field_items: #por siaca, me salia duplicado
                        field_items.append(text)

                divs = field.find_elements(By.CSS_SELECTOR, "div.field--item")
                for div in divs:
                    text = div.text.strip()
                    if text and text not in field_items:
                        field_items.append(text)

                field_text = " ".join(field_items).strip()
                
                print(f"{label}: {field_text}")
                all_scrapped += f"{label}: {field_text}\n"
            all_scrapped += "\n"

        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[title='Go to next page']"))
            )
            next_button_class = next_button.get_attribute("class")
            if "disabled" in next_button_class or "is-active" in next_button_class:
                print("No hay más páginas por scrapear")
                break
            else:
                next_button.click()
                print("Siguiente Pagina")
                WebDriverWait(driver, 10).until(
                    EC.staleness_of(content)
                )
        except Exception as e:
            print(f"Llegaste al limite: {e}")
            break

except Exception as e:
    print(f"Error al scrapear: {e}")

finally:
    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="nematode_data")
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(all_scrapped)

    with open(file_path, "rb") as file_data:
        object_id = fs.put(file_data, filename=os.path.basename(file_path))
        data = {
            "Objeto": object_id,
            "Tipo": "Web",
            "Url": url,
            "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["nematode", "biology", "samples"],
        }
        collection.insert_one(data)

    print(f"Datos guardados en archivo: {file_path} y en MongoDB")
    driver.quit()
