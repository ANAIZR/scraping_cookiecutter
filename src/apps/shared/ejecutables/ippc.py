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

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

url = "https://www.ippc.int/en/countries/south-africa/pestreports/"

try:
    driver.get(url)
    print("Ingresando a la URL")
    
    # Esperar a que la página cargue completamente
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.container>div.row")))

    # Analizar el contenido de la página principal
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Encontrar las filas en la tabla de publicaciones
    rows = soup.select("#publications tr")
    
    if rows:
        print(f"Se encontraron {len(rows)} filas.")
        for row in rows:
            # Para cada fila, buscar los enlaces dentro de las celdas (td)
            tds = row.find_all('td')
            for td in tds:
                link = td.find('a', href=True)
                if link:
                    href = link['href']
                    # Obtener el texto del enlace
                    text = link.get_text(strip=True)
                    print(f"Enlace encontrado: {text} - {href}")
                    
                    # Si el enlace es relativo, convertirlo a absoluto
                    if href.startswith('/'):
                        href = f"https://www.ippc.int{href}"
                    
                    # Acceder al enlace y hacer scraping de la página destino
                    print(f"Accediendo a la página: {href}")
                    driver.get(href)
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

                    # Scraping de la página de destino
                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    # Aquí puedes extraer los datos que necesitas, por ejemplo, el título de la página
                    page_title = page_soup.title.text if page_soup.title else 'Sin título'
                    print(f"Título de la página: {page_title}")

                    # Guardar o procesar los datos como desees, por ejemplo, guardar el contenido de la página
                    # Puedes guardar el contenido de la página en un archivo
                    with open(os.path.join(output_dir, f"{text}.html"), 'w', encoding='utf-8') as f:
                        f.write(str(page_soup))
                    print(f"Página guardada: {text}.html")
                    
                    # Regresar a la página principal después de procesar
                    driver.back()
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.container>div.row")))

    else:
        print("No se encontraron filas en la tabla de publicaciones.")
    
except Exception as e:
    print(f"Ocurrió un error: {e}")

finally:
    driver.quit()
