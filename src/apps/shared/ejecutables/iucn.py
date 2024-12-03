from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import hashlib
import os
from pymongo import MongoClient
import gridfs
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager

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

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=options
)
url = "https://www.iucnredlist.org/"
all_scraped = ""
visited_urls = set()  # Conjunto para almacenar enlaces ya visitados
try:
    # Navegar a la página principal
    driver.get(url)
    print("Esperando a que la página cargue...")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#redlist-js"))
    )

    # Clic en el botón de búsqueda
    btn = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search--site__button"))
    )
    btn.click()
    print("Botón clickeado.")

    # Esperar a que los artículos aparezcan
    WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div.cards--narrow article")
        )
    )

    while True:  # Iniciar un bucle para cargar más artículos hasta que no haya más
        # Obtener los artículos cargados en la página
        articles = driver.find_elements(By.CSS_SELECTOR, "div.cards--narrow article a")
        print(f"Se encontraron {len(articles)} enlaces.")

        for index, article in enumerate(articles):
            href = article.get_attribute("href")

            # Si ya hemos visitado este enlace, lo saltamos
            if href in visited_urls:
                continue

            print(f"Enlace {index + 1}: {href}")

            driver.get(href)
            print(f"Navegando a: {href}")

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("Página cargada.")

            try:
                title = WebDriverWait(driver, 30).until(
                    lambda d: d.find_element(
                        By.CSS_SELECTOR, "h1.headline__title"
                    ).text.strip()
                )
                print(f"Título de la página: {title}")
            except Exception as e:
                print(f"Error al obtener el título: {e}")
            try:
                taxonomy = WebDriverWait(driver, 30).until(
                    lambda d: d.find_element(By.CSS_SELECTOR, "#taxonomy").text.strip()
                )
                print(f"Taxonomia de la página: {taxonomy}")
            except Exception as e:
                print(f"Error al obtener la taxonomia: {e}")
            try:
                habitat = WebDriverWait(driver, 30).until(
                    lambda d: d.find_element(
                        By.CSS_SELECTOR, "#habitat-ecology"
                    ).text.strip()
                )
                print(f"Hábitat de la página: {habitat}")
            except Exception as e:
                print(f"Error al obtener el hábitat: {e}")

            text_content = title + taxonomy + habitat
            if title:
                all_scraped += text_content

            # Agregar la URL visitada al conjunto
            visited_urls.add(href)

            driver.back()
            print("Regresando a la página principal...")

        # Intentar hacer clic en el botón "Show more" si está presente
        try:
            show_more_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".section__link-out"))
            )
            show_more_btn.click()
            print("Clickeado 'Show more'. Esperando a que se carguen más artículos.")
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.cards--narrow article"))
            )
        except Exception as e:
            print("No se encontró el botón 'Show more' o no se pudo hacer clic.")
            break  # Salir del bucle si no se puede hacer clic más

    # Guardar los resultados en un archivo o base de datos como ya tienes en el código original
    folder_path = generate_directory(output_dir, url)
    file_path = get_next_versioned_filename(folder_path, base_name="umich")

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(all_scraped)
    except Exception as e:
        print(f"Error al escribir el archivo: {e}")

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

        print(f"Los datos se han guardado en MongoDB y el contenido se ha escrito en el archivo. ObjectId: {object_id}")

except Exception as e:
    print(f"Ocurrió un error: {e}")

finally:
    driver.quit()
