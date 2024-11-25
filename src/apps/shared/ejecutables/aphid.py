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

url = "http://aphid.aphidnet.org/"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

all_scraped_fact_sheets = ""
all_scraped_morphology = ""

try:

    driver.get(url)

    def scraper_first():
        global all_scraped_fact_sheets
        nav_fact_sheets = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    'nav.main #nav li:nth-child(4) a[href="species_list.php"]',
                )
            )
        )
        nav_fact_sheets.click()
        content = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#content"))
        )
        page_soup = BeautifulSoup(driver.page_source, "html.parser")
        faq_div = page_soup.select_one(".grid_8 #faq")
        h3_tags = faq_div.find_all("h3")

        for h3 in h3_tags:
            h3_id = h3.get("id")

            ul_tag = h3.find_next("ul")

            if ul_tag:
                li_tags = ul_tag.find_all("li")

                for li in li_tags:
                    a_tag = li.find("a", href=True)
                    if a_tag:
                        href = a_tag["href"]
                        text = a_tag.get_text(strip=True)

                        all_scraped_fact_sheets = f"Enlace: {href}\n + {text}\n\n"
                        driver.get(url + href)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "#content")
                            )
                        )

                        page_soup = BeautifulSoup(driver.page_source, "html.parser")
                        content = page_soup.select_one("#content div.grid_12")
                        if content:
                            hgroup = content.select_one("hgroup h1")
                            paragraphs = content.find_all("p", limit=4)
                            if hgroup:
                                all_scraped_fact_sheets += f"{hgroup.get_text()}\n"
                            for i, p in enumerate(paragraphs, start=1):
                                all_scraped_fact_sheets += f"{p.get_text()}\n"
                                    
                                

                            all_scraped_fact_sheets += "\n\n"
                        else:
                            print(
                                f"No se encontró contenido en #content div.grid_12 para el enlace: {href}"
                            )

    def scraper_second():
        global all_scraped_morphology
        nav_morphology = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "nav.main #nav li:nth-child(5)")
            )
        )

        ActionChains(driver).move_to_element(nav_morphology).perform()

        ul_tag = driver.find_element(
            By.CSS_SELECTOR, "nav.main #nav li:nth-child(5) ul"
        )
        li_tags = ul_tag.find_elements(By.TAG_NAME, "li")

        for index, li in enumerate(li_tags):
            try:
                if index == 0:
                    continue

                ul_tag = driver.find_element(
                    By.CSS_SELECTOR, "nav.main #nav li:nth-child(5) ul"
                )
                li_tags = ul_tag.find_elements(By.CSS_SELECTOR, "li")
                li = li_tags[index]

                a_tag = li.find_element(By.CSS_SELECTOR, "a")
                href = a_tag.get_attribute("href")
                driver.get(href)

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#content"))
                )

                page_soup = BeautifulSoup(driver.page_source, "html.parser")

                content = page_soup.select_one("section#content div.grid_8")
                if content:
                    hgroup = content.select_one("hgroup h1")
                    paragraphs = content.find("p")
                    portfolio = page_soup.select_one("section.portfolio ul#portfolio")

                    if  portfolio:
                        all_scraped_morphology += f"Enlace: {href}\n"
                        all_scraped_morphology += f"{hgroup.get_text()}\n"
                        all_scraped_morphology += f"{paragraphs.get_text(strip=True)}\n"
                        all_scraped_morphology += f"{portfolio.get_text()}\n\n"

            except Exception as e:
                print(f"Error procesando un elemento: {e}")

    #scraper_first()
    scraper_second()
    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="aphid")

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(all_scraped_fact_sheets + all_scraped_morphology)

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
