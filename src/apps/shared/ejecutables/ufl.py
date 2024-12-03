from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import hashlib

# Función para generar el directorio basado en la URL
def generate_directory(output_dir, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    folder_name = url.split("//")[-1].replace("/", "_") + "_" + url_hash[:8]
    folder_path = os.path.join(output_dir, folder_name)
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    return folder_path

# Configuración del navegador
chrome_options = Options()
chrome_options.add_argument("--headless")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

url = "https://specifyportal.floridamuseum.ufl.edu/iz/"
output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Definir la ruta completa para el archivo de salida
folder_path = generate_directory(output_dir, url)
file_path = os.path.join(folder_path, "scraped_data.txt")

# Abrir el archivo de salida para escritura
with open(file_path, "w", encoding="utf-8") as file:

    def scrape_page():
        # Esperar a que las filas de la tabla se carguen
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.x-grid-table tbody tr")))

        # Obtener el HTML actualizado de la página
        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("table.x-grid-table tbody tr:not(.x-grid-header-row)")

        print(f"Se encontraron {len(rows)} filas de datos.")

        # Extraer e imprimir los datos de las filas y guardarlos en el archivo
        all_scraped_data = []
        for row in rows:
            cols = row.find_all("td")
            data = [col.text.strip() for col in cols]
            all_scraped_data.append(data)
            print(data)

        # Escribir los datos en el archivo
        for data in all_scraped_data:
            file.write("\t".join(data) + "\n")

    def go_to_next_page():
        try:
            # Esperar a que el botón "Next Page" esté clickeable
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "button-1065-btnEl")))

            # Hacer clic en el botón de "Next Page"
            next_button = driver.find_element(By.ID, "button-1065-btnEl")
            next_button.click()
            print("Botón 'Next Page' clickeado")
            return True
        except Exception as e:
            print(f"No se pudo encontrar o hacer clic en el botón de 'Next Page': {e}")
            return False

    # Iniciar scraping
    driver.get(url)
    print("Ingresando a la URL")
    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl")))
    btn = driver.find_element(By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl")
    print("Botón encontrado")
    btn.click()  
    print("Botón clickeado")
    
    # Primer página de datos
    scrape_page()

    # Continuar con la siguiente página, si es posible
    while go_to_next_page():
        time.sleep(2)  # Esperar a que la página cargue
        scrape_page()

# Cerrar el navegador
driver.quit()
print(f"Datos guardados en el archivo: {file_path}")
