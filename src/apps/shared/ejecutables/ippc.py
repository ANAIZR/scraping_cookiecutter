from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select  # Importar Select
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
    
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.container>div.row")))

    # Esperar a que el select esté presente antes de interactuar con él
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "publications_length")))

    # Encontrar el elemento <select> y seleccionar la opción "All"
    select_element = driver.find_element(By.NAME, "publications_length")
    select = Select(select_element)
    
    # Seleccionar la opción "All"
    select.select_by_value("-1")
    print("Seleccionada la opción 'All'.")

    # Esperar que la página se actualice después de seleccionar "All"
    time.sleep(3)  # Esperar un poco para que la página recargue

    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    rows = soup.select("#publications tr")
    
    if rows:
        print(f"Se encontraron {len(rows)} filas.")
        for row in rows:
            tds = row.find_all('td')
            for td in tds:
                link = td.find('a', href=True)
                if link:
                    href = link['href']
                    text = link.get_text(strip=True)
                    print(f"Enlace encontrado: {text} - {href}")
                    
                    if href.startswith('/'):
                        href = f"https://www.ippc.int{href}"
                    
                    print(f"Accediendo a la página: {href}")
                    driver.get(href)
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    page_title = page_soup.title.text if page_soup.title else 'Sin título'
                    print(f"Título de la página: {page_title}")

                    with open(os.path.join(output_dir, f"{text}.html"), 'w', encoding='utf-8') as f:
                        f.write(str(page_soup))
                    print(f"Página guardada: {text}.html")
                    
                    driver.back()
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.container>div.row")))

    else:
        print("No se encontraron filas en la tabla de publicaciones.")
    
except Exception as e:
    print(f"Ocurrió un error: {e}")

finally:
    driver.quit()
