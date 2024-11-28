from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import hashlib
import os
from pymongo import MongoClient
import gridfs
from datetime import datetime
import time
from urllib.parse import urljoin  # Para manejar URLs relativas

# Directorio de salida donde se guardarán los archivos
output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)


# Función para generar un directorio basado en la URL
def generate_directory(output_dir, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    folder_name = (
        url.split("//")[-1].replace("/", "_").replace("?", "_").replace("=", "_")
        + "_"
        + url_hash[:8]
    )
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


client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)


url = "http://www.plantatlas.usf.edu"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
all_scrapped = ""


driver.get(url)
print(f"Entrando a la página: {url}")


try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "section#partners div.container")
        )
    )
    soup = BeautifulSoup(driver.page_source, "html.parser")
    print("Page loaded")
    time.sleep(4)
    print("Searching for section")
    section = soup.select_one("section#partners div.container")
    if section:
        print("Section found")
        time.sleep(2)
        print("Searching for containers")
        containers = section.select("div.partner-list")
        print("Containers found")
        time.sleep(2)
        for container in containers:
            cards = container.select("div.col-lg-3")
            for card in cards:
                print("Searching for card")
                title = card.select_one("h3").text
                link_card = card.select_one("a").get("href")
                print(f"Title: {title}")
                print(f"Link: {link_card}")
                if link_card:
                    driver.get(link_card)
                    print(f"***Navigating to the page****: {link_card}")
                    time.sleep(4)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#aspnetForm"))
                    )
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    btn = soup.select_one("#ctl00_cphHeader_ctrlHeader_btnBrowseSearch")
                    print("Searching for button")
                    if btn:
                        btn_selenium = driver.find_element(
                            By.ID, "ctl00_cphHeader_ctrlHeader_btnBrowseSearch"
                        )
                        WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(btn_selenium)
                        )  # Esperamos que el botón sea clickeable
                        btn_selenium.click()
                        print("Button clicked")
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "#ctl00_cphBody_Grid1")
                            )
                        )
                        soup = BeautifulSoup(driver.page_source, "html.parser")

                        table = soup.select_one("#ctl00_cphBody_Grid1")
                        if table:
                            rows = table.select("tr")
                            for row in rows:
                                cols = row.find_all("td")
                                if cols:
                                    # Extraer datos de cada celda de la fila
                                    data = [col.text.strip() for col in cols]
                                    #print(f"Data from row: {data}")
                                    print("Extracted")
                        else:
                            print("Table not found")

                    print("Eligiendo next button ")
                    next_button = driver.find_element(
                        By.ID, "ctl00_cphBody_Grid1_ctl01_ibNext"
                    )
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(next_button)
                    )

                    while next_button.is_enabled():
                        print("Clicking 'Next Page' button")
                        next_button.click()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "#ctl00_cphBody_Grid1")
                            )
                        )
                        soup = BeautifulSoup(driver.page_source, "html.parser")

                        table = soup.select_one("#ctl00_cphBody_Grid1")
                        if table:
                            rows = table.select("tr")
                            for row in rows:
                                cols = row.find_all("td")
                                if cols:
                                    # Extraer datos de cada celda de la fila
                                    data = [col.text.strip() for col in cols]
                                    #print(f"Data from row: {data}")
                                    print("Extraido")
                            next_button = driver.find_element(
                            By.ID, "ctl00_cphBody_Grid1_ctl01_ibNext"
                            )
                            WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable(next_button))
                        else:
                            print("Table not found")
                    else:
                        print("No more pages. Exiting pagination loop.")
                        break  
                else:
                    print("Button not found")
                time.sleep(4)
finally:
    driver.quit()
