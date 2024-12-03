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

# Ruta del directorio de salida
output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Generar nombre para la carpeta principal basado en la URL
def generate_main_folder(output_dir, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    folder_name = url.split("//")[-1].replace("/", "_") + "_" + url_hash[:8]
    folder_path = os.path.join(output_dir, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

# Generar nombre de archivo para el texto de salida
def get_output_file_path(folder_path):
    return os.path.join(folder_path, "output.txt")

# Inicialización de Selenium y MongoDB
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

url = "https://www.fws.gov/species/search"
all_scrapped = ""
base_url = "https://www.fws.gov"

# Crear la carpeta principal para la URL
main_folder = generate_main_folder(output_dir, url)
output_file_path = get_output_file_path(main_folder)

with open(output_file_path, "w", encoding="utf-8") as output_file:
    try:
        driver.get(url)
        print(f"Entrando a la página: {url}")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.default-view"))
        )

        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            print("Scraping...")

            cards = soup.select("div.default-view mat-card")

            if cards:
                print(f"Se encontraron {len(cards)} cards.")
                for card in cards:
                    link = card.find("a", href=True)
                    if link:
                        card_url = link["href"]
                        title = card.select_one("span")
                        all_scrapped += title.text + "\n"
                        full_url = base_url + card_url
                        driver.get(full_url)

                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )

                        soup_page = BeautifulSoup(driver.page_source, "html.parser")
                        content = soup_page.select_one("div.layout-stacked-side-by-side")
                        if content:
                            page_text = content.get_text()

                        output_file.write(f"Contenido de {card_url}:\n{page_text}\n\n")

                        with open(output_file_path, "rb") as file_data:
                            object_id = fs.put(file_data, filename=os.path.basename(output_file_path))

                            data = {
                                "Objeto": object_id,
                                "Tipo": "Web",
                                "Url": card_url,
                                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Etiquetas": ["planta", "plaga"],
                            }

                            collection.insert_one(data)
                            docs_count = collection.count_documents({"Url": card_url})

                            if docs_count > 2:
                                docs_for_url = collection.find({"Url": card_url}).sort("Fecha_scrapper", -1)
                                for doc in docs_for_url[2:]:
                                    collection.delete_one({"_id": doc["_id"]})
                                    fs.delete(doc["Objeto"])

                            print(f"Datos guardados en MongoDB y archivo en {output_file_path}. ObjectId: {object_id}")
                    else:
                        print("No se encontró un enlace en este card.")
            else:
                print("No se encontraron cards.")

            # Buscar el enlace a la siguiente página
            try:
                # Verificar el selector para el botón de la siguiente página
                next_button = driver.find_element(By.CSS_SELECTOR, ".search-pager__item")  # Cambiar a tu selector si es diferente
                print("Botón 'Siguiente' encontrado. Haciendo clic...")
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
                if next_button:
                    next_button.click()  # Hacer clic en el siguiente botón
                    print("Pasando a la siguiente página...")
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.default-view"))
                    )
                else:
                    print("No se encontró el botón para la siguiente página.")
                    break
            except Exception as e:
                print(f"No se pudo avanzar a la siguiente página: {e}")
                break

    except Exception as e:
        print(f"Error al entrar a la página {url}: {e}")

    finally:
        driver.quit()
