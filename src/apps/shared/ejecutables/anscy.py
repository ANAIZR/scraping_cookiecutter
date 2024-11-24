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
url = "http://poisonousplants.ansci.cornell.edu/php/plants.php"

# Inicialización del driver de Selenium
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Variable para guardar el contenido raspado
all_scraped = ""

try:
    driver.get(url)

    selector = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
        )
    )
    second_a = selector.find_elements(By.TAG_NAME, "a")[1]
    second_a.click()

    target_divs = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
        )
    )

    for div_index, target_div in enumerate(target_divs, start=1):
        urls = target_div.find_elements(By.TAG_NAME, "a")
        for link_index, link in enumerate(urls, start=1):
            link_href = link.get_attribute("href")
            driver.get(link_href)
            pageBody = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#mainContent #pagebody #main") 
                )
            )
            p_tags = pageBody.find_elements(By.TAG_NAME, "p")[:5]


            for i, p in enumerate(p_tags, start=1):

                all_scraped += p.text + "\n"


            driver.back()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
                )
            )


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
