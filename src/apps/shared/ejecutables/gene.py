from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import gridfs
import os
import hashlib
import time  
from selenium.webdriver.support.ui import Select

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
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)
url = "https://www.gene.affrc.go.jp/databases-micro_pl_diseases_en.php"
all_scrapped  = ""

def scroll_down_distance(driver, distance_cm=10):
    distance_px = int(distance_cm * 37.8)  
    driver.execute_script(f"window.scrollBy(0, {distance_px});")
    print(f"Desplazando hacia abajo {distance_cm} cm ({distance_px} píxeles).")
def scroll_up_distance(driver, distance_cm=10):
    distance_px = int(distance_cm * 37.8)  
    driver.execute_script(f"window.scrollBy(0, -{distance_px});")
    print(f"Desplazando hacia abajo {distance_cm} cm ({distance_px} píxeles).")

try:
    driver.get(url)
    print(f"Entrando a la página: {url}")
    print("viendo si vuelve")
    checkboxes = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "form#search div:nth-child(7) span:nth-child(2) input[type='checkbox']"))
    )
    for checkbox in checkboxes:
        if not checkbox.is_selected():  
            checkbox.click()

    btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "form#search input[type='submit']"))
    )
    btn.click()


    pagination_select = Select(driver.find_element(By.ID, "pagination"))


    for page_index in range(len(pagination_select.options)):
        print(f"{page_index + 1} de {len(pagination_select.options)}")
        try:
            pagination_select.select_by_index(page_index)
            print(f"Procesando página {page_index + 1}...")

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.table-responsive tbody"))
            )
            rows = driver.find_elements(By.CSS_SELECTOR, "div.table-responsive tbody tr")
            print(f"Se encontraron {len(rows)} filas en la página {page_index + 1}.")

            for index in range(len(rows)):
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, "div.table-responsive tbody tr")
                    current_row = rows[index]

                    print(f"Fila {index + 1} encontrada.")
                    second_td = current_row.find_element(By.CSS_SELECTOR, "td:nth-child(2) a")
                    link = second_td.get_attribute("href")
                    print(f"Haciendo clic en el enlace: {link}")

                    original_window = driver.current_window_handle
                    second_td.click()
                    print("Abriendo la nueva pestaña...")
                    WebDriverWait(driver, 15).until(lambda d: len(d.window_handles) > 1)
                    new_window = [window for window in driver.window_handles if window != original_window][0]
                    driver.switch_to.window(new_window)
                    print("Cambiando a la nueva pestaña...")
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
                    print(f"{all_scrapped} \n")
                    print("Datos extraídos correctamente.")

                    driver.close()
                    print("Cerrando la pestaña actual.")
                    driver.switch_to.window(original_window)
                    print("Regresando a la pestaña original.")
                    if (index + 1) % 12 == 0:
                        scroll_down_distance(driver, distance_cm=20)
                    if (index + 1) == len(rows):
                        scroll_up_distance(driver, distance_cm=25)
                except Exception as e:
                    print(f"Error al procesar la fila: {e}")
                    if driver.current_window_handle != original_window:
                        driver.switch_to.window(original_window)
                    continue

        except Exception as e:
            print(f"Error al procesar la página {page_index + 1}: {e}")




    soup = BeautifulSoup(driver.page_source, "html.parser")
    text_content = soup.get_text(separator="\n", strip=True)
    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="iucngisd")
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

except Exception as e:
    print(f"Ocurrió un error: {e}")

finally:
    driver.quit()
