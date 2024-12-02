from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import hashlib
import os
from pymongo import MongoClient
import gridfs
from datetime import datetime
import time
# Directorio de salida donde se guardarán los archivos
output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Función para generar un directorio basado en la URL
def generate_directory(output_dir, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    folder_name = url.split("//")[-1].replace("/", "_").replace("?","_").replace("=","_") + "_" + url_hash[:8]
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

url = "https://jb.utad.pt/chavedicotomica/inversa/todas"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
all_scrapped = ""

driver.get(url)
print(f"Entrando a la página: {url}")

while True:  
    print("Vuevlo a entrar al while")
    try:
        

        content = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody"))
        )
        
        rows = driver.find_elements(By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody tr")
        print(f"Filas encontrads {len(rows)}")
        for row in rows:
            first_td = row.find_element(By.CSS_SELECTOR, "td a")
            link = first_td.get_attribute("href")
            
            driver.get(link)
            print(f"***NAVEGANDO A LA PAGINA****: {link}")

            content = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section.container div.rfInv"))
            )
            cards = driver.find_elements(By.CSS_SELECTOR, "div.col-md-2")
            print(f"Cantidad de cards encontradas {len(cards)}")
            for card in cards:
                link_in_card = card.find_element(By.CSS_SELECTOR, "a")
                card_href = link_in_card.get_attribute("href")
                link_in_card.click()

                original_window = driver.current_window_handle
                all_windows = driver.window_handles
                new_window = [window for window in all_windows if window != original_window][0]

                driver.switch_to.window(new_window)

                new_page_content = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "main.container div.parteesq"))
                )
                extracted_text = new_page_content.text 

                all_scrapped += f"Datos extraídos de {driver.current_url}\n"
                all_scrapped += extracted_text + "\n" 
                driver.close()
                driver.switch_to.window(original_window)
            
            driver.back() 
            time.sleep(2)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody"))
            )

        next_button = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0_next a"))
        )
        
        if "disabled" in next_button.get_attribute("class"): 
            print("No hay más páginas, terminando el scraping.")
            break  
        
        next_button.click()

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody"))
        )

    except Exception as e:
        break  

folder_path = generate_directory(output_dir, url)
file_path = get_next_versioned_filename(folder_path, base_name="flora")

with open(file_path, "w", encoding="utf-8") as file:
    file.write(all_scrapped)

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

driver.quit()
