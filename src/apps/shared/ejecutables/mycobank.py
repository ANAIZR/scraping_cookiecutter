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
options.add_argument("--headless")  # Ejecutar en modo headless (sin interfaz)
options.add_argument("--window-size=1920,1080")  # Forzar resolución fija
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

if not os.path.exists(os.path.dirname(output_dir)):
    os.makedirs(os.path.dirname(output_dir))

def save_to_file(content, file_path):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(content + "\n")
        f.write("*" * 40 + "\n")

# Navegar a la página deseada
url = "https://www.mycobank.org/Simple%20names%20search"
driver.get(url)
# Crear carpeta y archivo para almacenar el contenido
folder_path = generate_directory(output_dir, url)
file_path = get_next_versioned_filename(folder_path, base_name="mycobank")
try:
    wait = WebDriverWait(driver, 10)
    search_button = wait.until(EC.element_to_be_clickable((By.ID, "search-btn")))
    search_button.click()
    print("Se hizo clic en el botón de búsqueda.")
except Exception as e:
    print(f"Error al hacer clic en el botón Search: {e}")
    driver.quit()
    exit()

time.sleep(5)  # Esperar carga inicial
rows = driver.find_elements(By.CSS_SELECTOR, "tbody[role='rowgroup'] tr")

print(f"Número total de filas encontradas: {len(rows)}")

# Iterar sobre las filas
for index, row in enumerate(rows, start=1):
    try:
        time.sleep(1)
        link = row.find_element(By.CSS_SELECTOR, "td a")
        link_name = link.text.strip()
        driver.execute_script("arguments[0].click();", link)
        
        time.sleep(2)
        popup = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.dockmodal-body")))
        popup_content = popup.text.strip()
        
        content_to_save = f"# {index} - SITIO: {link_name}\nContenido:\n{popup_content}"
        save_to_file(content_to_save, output_dir)
        
        close_button = driver.find_element(By.CSS_SELECTOR, "a.header-action.action-close")
        driver.execute_script("arguments[0].click();", close_button)
        print(f"Popup procesado y cerrado para {link_name}.")
    except Exception as e:
        print(f"Error al procesar la fila {index}: {e}")
        continue

driver.quit()
print(f"Contenido guardado en: {output_dir}")
