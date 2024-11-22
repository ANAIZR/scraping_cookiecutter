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

url = "https://wiki.bugwood.org/Main_Page"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))


try:
    driver.get(url)

    search_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "#mw-navigation container-fluid #mw-navigation-collapse #mainContent #content #pagebody #main div form table:nth-of-type(2) input[type='submit']",
            )
        )
    )
    search_button.click()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#wrapper #nonFooter #container #mainContent #content #pagebody #main table"))  
    )
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    text_content = soup.get_text(separator='\n', strip=True)
    print(text_content)
finally:
    driver.quit()
