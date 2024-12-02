from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
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

base_url = "https://www.ndrs.org.uk/"
volumes_url = "https://www.ndrs.org.uk/volumes.php"

try:
    # Navegar a la página principal de contenedores
    driver.get(volumes_url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent")))

    # Extraer los enlaces de los contenedores
    soup = BeautifulSoup(driver.page_source, "html.parser")
    containers = soup.select("#MainContent .volumes")  # Asegúrate de que el selector sea correcto

    # Verificar que haya contenedores
    if not containers:
        print("No se encontraron contenedores en la página.")
        driver.quit()
    
    # Iterar sobre cada contenedor
    for index, container in enumerate(containers):
        title = container.select_one("h2").text.strip() if container.select_one("h2") else 'No Title'
        print(f"Procesando contenedor {index + 1}: {title}")

        enlace = container.select_one("a")['href'] if container.select_one("a") else None
        if enlace:
            container_url = base_url + enlace
            print(f"Accediendo al contenedor {index + 1}: {container_url}")

            # Navegar al contenedor
            driver.get(container_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

            # Asegurarse de que la página se haya cargado completamente
            print("Esperando que la página de contenedor se cargue completamente...")
            time.sleep(3)  # Aumentar el tiempo de espera si es necesario

            # Obtener los enlaces de los artículos dentro del contenedor
            page_soup = BeautifulSoup(driver.page_source, "html.parser")
            article_list = page_soup.select("ul.clist li a")

            if not article_list:
                print("No se encontraron artículos dentro de este contenedor.")
                continue  # Si no hay artículos, pasar al siguiente contenedor

            # Iterar sobre cada artículo dentro del contenedor
            for article in article_list:
                article_title = article.text.strip()
                article_url = article['href']
                article_full_url = base_url + article_url

                print(f"Articulo: {article_title}")
                print(f"Enlace del artículo: {article_full_url}")

                # Navegar al artículo y obtener su contenido
                driver.get(article_full_url)
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

                # Extraer el contenido del artículo
                article_soup = BeautifulSoup(driver.page_source, "html.parser")
                article_title_text = article_soup.title.text if article_soup.title else 'No Title'
                print(f"Título del artículo: {article_title_text}")

                # Aquí puedes extraer otros datos del artículo, como contenido, autores, etc.

            # Regresar a la página de contenedores después de procesar los artículos
            print("Regresando a la página de contenedores...")
            driver.get(volumes_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent")))

            # Asegúrate de que la página se recargue antes de continuar
            time.sleep(3)  # Ajustar tiempo si es necesario

            # Volver a obtener los contenedores después de regresar
            soup = BeautifulSoup(driver.page_source, "html.parser")
            containers = soup.select("#MainContent .volumes")  # Reprocesamos los contenedores
            print(f"Se encontraron {len(containers)} contenedores después de regresar a la página.")

            # Verificar si hay más contenedores para procesar
            if len(containers) <= index + 1:
                print("No hay más contenedores para procesar.")
                break  # Si ya no hay más contenedores, salir del ciclo

            # Espera adicional antes de continuar al siguiente contenedor
            print("Listo para procesar el siguiente contenedor.")
            time.sleep(2)

except Exception as e:
    print(f"Ocurrió un error: {e}")

finally:
    driver.quit()
