from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import gridfs
import os
import hashlib
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

output_file_path = os.path.join(output_dir, "output.txt")

with open(output_file_path, "w", encoding="utf-8") as output_file:
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    url = "https://www.gene.affrc.go.jp/databases-micro_pl_diseases_en.php"
    all_scrapped = ""

    try:
        driver.get(url)
        print(f"Entrando a la página: {url}")

        checkboxes = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "form#search div:nth-child(7) span:nth-child(2) input[type='checkbox']"))
        )
        print(f"Se encontraron {len(checkboxes)} checkboxes.")
        for checkbox in checkboxes:
            if not checkbox.is_selected():
                print(f"Seleccionando checkbox: {checkbox.get_attribute('value')}")
                driver.execute_script("arguments[0].click();", checkbox)

        print("Checkboxes seleccionados.")
        print("Haciendo clic en el botón de búsqueda...")
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "form#search input[type='submit']"))
        )
        driver.execute_script("arguments[0].click();", btn)

        pagination_select = Select(driver.find_element(By.ID, "pagination"))

        for page_index in range(1, len(pagination_select.options) + 1):
            print(f"Procesando página {page_index + 1} de {len(pagination_select.options)}...")

            try:
                pagination_select.select_by_index(page_index)

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.table-responsive"))
                )

                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')

                rows = soup.select("div.table-responsive tbody tr")
                print(f"Se encontraron {len(rows)} filas en la página {page_index + 1}.")

                for index, current_row in enumerate(rows):
                    try:
                        print(f"Procesando fila {index + 1} de la página {page_index + 1}...")
                        second_td = current_row.select_one("td:nth-child(2) a")
                        link = second_td.get("href")
                        print(f"Haciendo clic en el enlace: {link}")

                        driver.execute_script("window.open(arguments[0]);", link)
                        original_window = driver.current_window_handle
                        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
                        new_window = [window for window in driver.window_handles if window != original_window][0]
                        driver.switch_to.window(new_window)

                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.container table.table"))
                        )
                        print(f"Contenido cargado en la nueva pestaña: {driver.current_url}")

                        content = WebDriverWait(driver, 25).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.container div>table tbody"))
                        )
                        time.sleep(2)
                        all_scrapped += content.text
                        print("Extrayendo datos...")
                        print("SCRAPPED DATA: ", all_scrapped)
                        rows = content.find_elements(By.TAG_NAME, "tr")

                        for row in rows:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            headers = row.find_elements(By.TAG_NAME, "th")

                            row_text = ""
                            if headers:
                                for header in headers:
                                    row_text += header.text.strip() + ": "  

                            for cell in cells:
                                row_text += cell.text.strip() + "\n" 

                            output_file.write(row_text.strip() + "\n") 

                        with open(output_file_path, "rb") as file_data:
                            object_id = fs.put(file_data, filename=os.path.basename(output_file_path))
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

                        print(f"Los datos se han guardado en MongoDB y el contenido se ha escrito en el archivo. ObjectId: {object_id}")

                        driver.close()
                        print("Cerrando la pestaña actual.")
                        driver.switch_to.window(original_window)
                        print("Regresando a la pestaña original.")

                    except Exception as e:
                        print(f"Error al procesar la fila: {e}")
                        if driver.current_window_handle != original_window:
                            driver.switch_to.window(original_window)
                        continue

            except Exception as e:
                print(f"Error al procesar la página {page_index + 1}: {e}")

        print("Scraping completado.")

    except Exception as e:
        print(f"Ocurrió un error: {e}")

    finally:
        driver.quit()
