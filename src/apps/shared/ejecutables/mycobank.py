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
url = "https://www.mycobank.org/Simple%20names%20search"
driver.get(url)

# Esperar a que la página cargue completamente
time.sleep(5)  # Ajusta este tiempo según sea necesario

try:
    wait = WebDriverWait(driver, 10)  # Esperar hasta 10 segundos
    search_button = wait.until(EC.element_to_be_clickable((By.ID, "search-btn")))
    search_button.click()
    print("Se hizo clic en el botón de búsqueda.")
except Exception as e:
    print(f"Error al hacer clic en el botón Search: {e}")
    driver.quit()
    exit()

# Obtener el HTML de la página
time.sleep(5)
html_content = driver.page_source

# Usar BeautifulSoup para analizar el HTML
soup = BeautifulSoup(html_content, "html.parser")

# Esperar a que la tabla cargue
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody[role='rowgroup']")))

# Recoger todas las filas sin depender del scroll
rows = driver.find_elements(By.CSS_SELECTOR, "tbody[role='rowgroup'] tr")
print(f"Número total de filas encontradas: {len(rows)}")

# Crear carpeta y archivo para almacenar el contenido
folder_path = generate_directory(output_dir, url)
file_path = get_next_versioned_filename(folder_path, base_name="scrape")

# Abrir el archivo en modo 'a' para agregar contenido después de cada ciclo
with open(file_path, 'w', encoding='utf-8') as f:
    # Iterar sobre cada fila y abrir el popup
    for index, row in enumerate(rows, start=1):
        try:
            # Obtener el enlace dentro de la fila
            time.sleep(1)
            link = row.find_element(By.CSS_SELECTOR, "td a")
            time.sleep(1)
            link_name = link.find_element(By.CSS_SELECTOR, "div.text-overflow").text.strip()
            #link_name=link.text.strip()  # Asegúrate de obtener el texto correctamente
            print(f"Haciendo clic en {index}: : {link_name}")
            
            driver.execute_script("arguments[0].click();", link)  # Usar JavaScript para asegurar el clic

            time.sleep(2)

            # Esperar a que el popup se haga visible
            popup = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.dockmodal-body")))

            # Extraer el contenido de texto dentro del popup
            popup_content = popup.text.strip()

            # Guardar el contenido del popup en el archivo durante cada ciclo
            f.write(f"Contenido del listado {index}: {link_name}:\n")
            f.write(f"{popup_content}\n")
            f.write("-" * 80 + "\n")  # Separador entre los contenidos
            f.flush()
            # Imprimir el contenido del popup para verificar
            #print(f"Contenido del popup para {link_text}:")
            #print(popup_content)

            # Cerrar el popup
            close_button = driver.find_element(By.CSS_SELECTOR, "a.header-action.action-close")
            driver.execute_script("arguments[0].click();", close_button)  # Usar JavaScript para asegurar el clic
            print(f"Popup cerrado para {index}: {link_name}")
            time.sleep(1)
        except Exception as e:
            print(f"Error al procesar el enlace en la fila {index}: {e}")
            continue



# Cerrar el navegador al finalizar
driver.quit()
print(f"Contenido guardado en: {file_path}")