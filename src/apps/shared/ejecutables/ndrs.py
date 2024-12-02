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
    driver.get(volumes_url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent")))

    soup = BeautifulSoup(driver.page_source, "html.parser")
    containers = soup.select("#MainContent .volumes") 

    if not containers:
        print("No se encontraron contenedores en la página.")
        driver.quit()
    
    for index, container in enumerate(containers):
        title = container.select_one("h2").text.strip() if container.select_one("h2") else 'No Title'
        print(f"Procesando contenedor {index + 1}: {title}")

        enlace = container.select_one("a")['href'] if container.select_one("a") else None
        if enlace:
            container_url = base_url + enlace
            print(f"Accediendo al contenedor {index + 1}: {container_url}")

            driver.get(container_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

            print("Esperando que la página de contenedor se cargue completamente...")
            time.sleep(3) 

            page_soup = BeautifulSoup(driver.page_source, "html.parser")
            article_list = page_soup.select("ul.clist li a")

            if not article_list:
                print("No se encontraron artículos dentro de este contenedor.")
                continue  

            for article in article_list:
                article_title = article.text.strip()
                article_url = article['href']
                article_full_url = base_url + article_url

                print(f"Articulo: {article_title}")
                print(f"Enlace del artículo: {article_full_url}")

                driver.get(article_full_url)
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

                article_soup = BeautifulSoup(driver.page_source, "html.parser")
                article_title_text = article_soup.title.text if article_soup.title else 'No Title'
                print(f"Título del artículo: {article_title_text}")


            print("Regresando a la página de contenedores...")
            driver.get(volumes_url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent")))

            time.sleep(3) 

            soup = BeautifulSoup(driver.page_source, "html.parser")
            containers = soup.select("#MainContent .volumes")  
            print(f"Se encontraron {len(containers)} contenedores después de regresar a la página.")

            if len(containers) <= index + 1:
                print("No hay más contenedores para procesar.")
                break  
            print("Listo para procesar el siguiente contenedor.")
            time.sleep(2)

except Exception as e:
    print(f"Ocurrió un error: {e}")

finally:
    driver.quit()
