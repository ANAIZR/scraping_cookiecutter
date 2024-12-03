from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

url = "http://pnwhandbooks.org/plantdisease/"
driver.get(url)

def scrape_current_page():
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.view-content div.views-row"))
        )
        containers = driver.find_elements(By.CSS_SELECTOR, "div.view-content div.views-row")
        print(f"Contenedores encontrados en esta página: {len(containers)}")

        for container in containers:
            link = container.find_element(By.CSS_SELECTOR, "div.views-field-title a")
            href = link.get_attribute("href")
            print(f"Enlace encontrado: {href}")

            driver.get(href)
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            title = soup.find('h1')
            if title:
                print(f"Título de la página: {title.get_text()}")

            driver.back()
            time.sleep(2)

    except Exception as e:
        print(f"Error al procesar la página actual: {e}")

def go_to_next_page():
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, "li.next a")
        next_button.click()
        time.sleep(3) 
        return True
    except Exception as e:
        print("No se encontró el botón 'Next'. Fin de la paginación.")
        return False

try:
    time.sleep(5)
    boton = driver.find_element(By.CSS_SELECTOR, "#edit-submit-plant-subarticles-autocomplete")
    boton.click()
    time.sleep(3)

    while True:
        print("Scrapeando la página actual...")
        scrape_current_page()

        if not go_to_next_page():
            break

except Exception as e:
    print(f"Error durante el proceso de scraping: {e}")
finally:
    driver.quit()
