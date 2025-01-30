from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from ..functions import process_scraper_data, initialize_driver, get_logger, load_keywords

logger = get_logger("scraper")

def scrape_pages(driver, keywords):
    all_scraper = ""
    
    for keyword in keywords:
        try:
            # Ingresar la palabra clave en el input con id 'qs'
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "qs"))
            )
            search_input.clear()
            search_input.send_keys(keyword)
            search_input.submit()
            time.sleep(random.uniform(2, 4))
            
            # Esperar a que aparezcan los resultados y obtener los hrefs
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "srp-results-list"))
            )
            results_list = driver.find_elements(By.CSS_SELECTOR, "#srp-results-list a")
            urls = [result.get_attribute("href") for result in results_list]
            
            for url in urls:
                driver.get(url)
                time.sleep(random.uniform(2, 4))
                
                # Extraer el texto del div con id 'abstracts'
                try:
                    abstract_text = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "abstracts"))
                    ).text
                    
                    all_scraper += f"{abstract_text}\n"
                except Exception as e:
                    logger.error(f"Error extrayendo abstracts de {url}: {e}")
                    continue
                
                # Volver a la segunda página
                driver.back()
                time.sleep(random.uniform(2, 4))
            
            # Volver a la primera página
            driver.back()
            time.sleep(random.uniform(2, 4))
        
        except Exception as e:
            logger.error(f"Error procesando la palabra clave {keyword}: {e}")
            continue
    
    # Procesar los datos extraídos
    process_scraper_data(all_scraper)

def scraper_sciencedirect(url, sobrenombre):
    logger.info(f"Iniciando scraping en {url} con sobrenombre {sobrenombre}")
    
    driver = initialize_driver()
    keywords = load_keywords()  # Función para cargar palabras clave desde un archivo

    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))
        scrape_pages(driver, keywords)
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {e}")
    finally:
        driver.quit()
