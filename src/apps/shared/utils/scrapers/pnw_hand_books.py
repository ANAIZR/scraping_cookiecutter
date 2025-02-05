from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
import random
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_pnw_hand_books(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = []  
    
    try:
        driver.get(url)
        
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#edit-submit-plant-subarticles-autocomplete"))
            )
            driver.execute_script("arguments[0].click();", button)
        except Exception as e:
            logger.error(f"No se pudo encontrar o hacer clic en el botón inicial: {e}")
            return Response({"error": "Botón no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
        
        def scrape_current_page():
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.view-content"))
                )
                containers = driver.find_elements(By.CSS_SELECTOR, "div.view-content div.views-row")
                
                for container in containers:
                    try:
                        link = container.find_element(By.CSS_SELECTOR, "div.views-field-title a")
                        href = link.get_attribute("href")
                        
                        driver.get(href)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
                        )
                        
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        title = soup.find("h1")
                        content = soup.find("div", class_="region-content")
                        
                        if title and content:
                            all_scraper.append(f"URL: {href}\n\n{title.text}\n{content.text}\n")
                        else:
                            logger.warning(f"No se encontró contenido en {href}")
                        
                        driver.back()
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.view-content"))
                        )
                        time.sleep(random.uniform(1, 2))
                    except Exception as e:
                        logger.error(f"Error procesando un enlace: {e}")
            except Exception as e:
                logger.error(f"Error al procesar la página actual: {e}")
        
        def go_to_next_page():
            try:
                next_buttons = driver.find_elements(By.CSS_SELECTOR, "li.next a")
                if next_buttons:
                    driver.execute_script("arguments[0].click();", next_buttons[0])
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.view-content"))
                    )
                    return True
                return False
            except Exception as e:
                logger.info("No se encontró el botón 'Next'. Fin de la paginación.")
                return False

        while True:
            scrape_current_page()
            if not go_to_next_page():
                break
        
        response = process_scraper_data("\n".join(all_scraper), url, sobrenombre, collection, fs)
        return response
    
    except Exception as e:
        logger.error(f"Error general en el scraper: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        driver.quit()
