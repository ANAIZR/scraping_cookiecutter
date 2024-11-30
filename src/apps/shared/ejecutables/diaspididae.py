from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
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
    sanitized_url = url.split("//")[-1].replace("/", "_").replace("?", "_").replace("=", "_").replace("&", "_")
    folder_name = f"{sanitized_url}_{url_hash[:8]}"
    folder_path = os.path.join(output_dir, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def get_next_versioned_filename(folder_path, base_name="diaspididae_data"):
    version = 0
    while True:
        file_name = f"{base_name}_v{version}.txt"
        file_path = os.path.join(folder_path, file_name)
        if not os.path.exists(file_path):
            return file_path
        version += 1

def clean_text(text):
    return " ".join(text.split()).strip()

def format_scraped_data_with_headers(html_content):
    """Formatea el contenido scraped para separar encabezados en líneas nuevas."""
    soup = BeautifulSoup(html_content, "html.parser")
    formatted_text = ""
    for element in soup.find_all(recursive=False):
        if element.name == "b": 
            formatted_text += f"\n{element.get_text()}\n"
        elif element.get_text(strip=True): 
            formatted_text += f"{element.get_text(separator=' ')} "
    return formatted_text.strip()

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
start_lookupid = 113039

all_scrapped = ""
url = f"https://diaspididae.linnaeus.naturalis.nl/linnaeus_ng/app/views/species/taxon.php?id={start_lookupid}"

def scrape_species(driver, lookupid):
    """Realiza el scraping para un `lookupid` específico."""
    base_url = "https://diaspididae.linnaeus.naturalis.nl/linnaeus_ng/app/views/species/taxon.php"
    full_url = f"{base_url}?id={lookupid}"
    
    driver.get(full_url)
    print(f"Scraping de la página: {full_url}")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#content.taxon-detail"))
        )
        content_div = driver.find_element(By.CSS_SELECTOR, "div#content.taxon-detail")
        html_content = content_div.get_attribute("innerHTML")
    except Exception as e:
        print(f"Error al cargar contenido de la página {lookupid}: {e}")
        return None

    soup = BeautifulSoup(html_content, "html.parser")
    scraped_data = {}

    scraped_data["text"] = format_scraped_data_with_headers(html_content)

    return {
        "text": scraped_data["text"],
    }

try:
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "p.row"))
    )
    elements = driver.find_elements(By.CSS_SELECTOR, "p.row")
    lookup_ids = [el.get_attribute("lookupid") for el in elements]
    print(f"Lookup IDs encontrados: {lookup_ids}")

    for lookupid in lookup_ids:
        scraped_data = scrape_species(driver, lookupid)
        if scraped_data:
            all_scrapped += f"{scraped_data['text']}\n\n"
            all_scrapped += "\n\n"

finally:
    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="diaspididae_data")
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(all_scrapped)

    with open(file_path, "rb") as file_data:
        object_id = fs.put(file_data, filename=os.path.basename(file_path))
        data = {
            "Objeto": object_id,
            "Tipo": "Web",
            "Url": url,
            "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["diaspididae", "biology", "taxonomy"],
        }
        collection.insert_one(data)

    print(f"Datos guardados en archivo: {file_path} y en MongoDB")
    driver.quit()
