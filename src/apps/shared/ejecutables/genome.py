from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import os
import hashlib

# Configurar Selenium (aquí con Chrome)
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")  # Maximiza la ventana
driver = webdriver.Chrome(options=options)


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


# Navegar a la página deseada
url = "https://www.genome.jp/virushostdb/view/"
driver.get(url)

# Esperar a que la página cargue completamente
time.sleep(5)  # Ajusta este tiempo según sea necesario


def extract_data(driver, file, record_count):
    """
    Extrae datos del segundo tbody y los guarda en un archivo en el formato especificado.
    """
    try:
        # Seleccionar el segundo tbody
        tbody = driver.find_element(By.XPATH, "//table/tbody[2]")
        rows = tbody.find_elements(By.CSS_SELECTOR, "tr")

        for row in rows:
            cols = row.find_elements(By.CSS_SELECTOR, "td")
            
            # Verifica si la fila tiene al menos 4 columnas
            if len(cols) < 4:
                print(f"Fila {record_count} no tiene suficientes columnas. Skipping...")
                continue
            
            # Extrae los datos de cada columna con seguridad
            titulo = cols[0].get_attribute('innerText').strip()
            descripcion = cols[1].get_attribute('innerText').strip()
            host_name = cols[2].get_attribute('innerText').strip()
            tipos = cols[3].get_attribute('innerText').strip()

            # Guarda en el archivo
            file.write(f"Registro #{record_count} : \n")
            file.write(f"Virus(species) name :      {titulo}\n")
            file.write(f"Virus lineage       :      {descripcion}\n")
            file.write(f"Host name           :      {host_name}\n")
            file.write(f"Host lineage        :      {tipos}\n")
            file.write("-------------------------------------------\n\n")

            record_count += 1

        return record_count
    except Exception as e:
        print(f"Error al extraer datos: {e}")
        return record_count

def navigate_to_next_page(driver):
 
    try:
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.next"))
        )
        next_button.click()
        time.sleep(1)
        return True
    except Exception as e:
        print(f"No se pudo hacer clic en 'Next': {e}")
        return False

# Número total de páginas y contador de registros
total_pages = 1664  # Aproximado
current_page = 1
record_count = 1
# Crear carpeta y archivo para almacenar el contenido
folder_path = generate_directory(output_dir, url)
file_path = get_next_versioned_filename(folder_path, base_name="genome")

try:
    # Abre el archivo en modo escritura
    with open(file_path, "w", encoding="utf-8") as file:
        while current_page <= total_pages:
            print(f"Procesando página {current_page}/{total_pages}...")
            # Extraer datos de la tabla
            record_count = extract_data(driver, file, record_count)
            
            # Navegar a la siguiente página
            if current_page < total_pages:
                if not navigate_to_next_page(driver):
                    break  # Si no se puede navegar, detener el bucle
            current_page += 1
finally:
    driver.quit()

print(f"Scraping completo. Los resultados están en {file_path}")