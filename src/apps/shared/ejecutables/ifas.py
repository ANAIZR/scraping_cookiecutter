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
from selenium.webdriver.common.action_chains import ActionChains
import time
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

url = "https://plant-directory.ifas.ufl.edu/plant-directory/"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

all_scrapper =""
try:
    driver.get(url)
    print("Entrando a la página:", url)
    time.sleep(5)
    print("Página cargada correctamente.")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#app section.plant-cards"))
    )
    print("Contenido encontrado.")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    print("Contenido encontrado 2.")
    content = soup.select_one("#app section.plant-cards")
    if content:
        print("Contenido encontrado. Buscaremos los cards")
        cards = content.select("ul.plants li.plant") 
        
        for i, card in enumerate(cards, start=1):
            print(f"Procesando card {i}.")
            
            link_card_element = card.select_one("a")
            if link_card_element:
                link_card = link_card_element.get("href")
                print(f"Link encontrado: {link_card}")
                if link_card:
                    base_url = f"{url+link_card}"
                    print(f"Entrando a la página: {base_url}")
                    driver.get(base_url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "section.plant-page"))
                    )
                    print("Página cargada correctamente.")
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    title = soup.select_one("h2.plain").get_text(strip=True)
                    print("Título encontrado:", title)
                    conteiner = soup.select_one("div.content")
                    if conteiner:
                        print("Contenido encontrado.")
                        primary_content = conteiner.select("div.primary div[style*='margin:2rem']")
                        second_content = conteiner.select("div.primary div[style*='margin-bottom:2rem']")
                        all_content = "\n".join([element.get_text(strip=True) for element in primary_content + second_content])
                        all_scrapper += all_content 
                        folder_path = generate_directory(output_dir, link_card)
                        print(f"Directorio creado: {folder_path}")
                        file_path = get_next_versioned_filename(folder_path, "contenido")
                        with open(file_path, "w", encoding="utf-8") as file:
                            file.write(all_scrapper)
                        print(f"Contenido guardado en: {file_path}")
                    else:
                        print(f"No se encontró contenido en la tarjeta {i}.")
            else:
                print(f"No se encontró un enlace en la tarjeta {i}.")
            time.sleep(1)  
finally:
    driver.quit()
