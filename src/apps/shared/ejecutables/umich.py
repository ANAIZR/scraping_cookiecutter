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


client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

url = "https://lsa.umich.edu/herbarium/collections.html"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

try:
    driver.get(url)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#content"))
    )
    text_content = soup.get_text(separator="\n", strip=True)
    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="umich")
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text_content)

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
        print(
            f"Los datos se han guardado en MongoDB y el contenido se ha escrito en el archivo. ObjectId: {object_id}"
        )

finally:
    driver.quit()
