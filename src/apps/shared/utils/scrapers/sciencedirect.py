from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
import os
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    get_next_versioned_filename,
    load_keywords
)

def recursive_scraper(driver, keywords, index, all_scraper):
    if index >= len(keywords):
        return all_scraper  # Caso base: cuando se procesan todas las palabras clave
    
    keyword = keywords[index]
    print(f"Buscando con la palabra clave {index + 1}: {keyword}")
    try:
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "qs"))
        )
        search_input.clear()
        search_input.send_keys(keyword)
        search_input.submit()
        time.sleep(random.uniform(3, 5))
        
        # Esperar a que aparezcan los resultados
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "srp-results-list"))
        )
        
        # Obtener los enlaces de los resultados
        page_soup = BeautifulSoup(driver.page_source, "html.parser")
        results = page_soup.select("#srp-results-list a")
        hrefs = [a["href"] for a in results if a.get("href")]
        
        print(f"Resultados encontrados: {len(hrefs)}")
        
        for href in hrefs:
            driver.get(href)
            time.sleep(random.uniform(3, 5))
            
            # Extraer el abstract
            page_soup = BeautifulSoup(driver.page_source, "html.parser")
            abstract_div = page_soup.find("div", id="abstracts")
            if abstract_div:
                all_scraper += abstract_div.get_text(strip=True) + "\n"
            
            driver.back()
            time.sleep(random.uniform(2, 4))
        
    except Exception as e:
        print(f"Error con la palabra clave {keyword}: {e}")
    
    return recursive_scraper(driver, keywords, index + 1, all_scraper)  # Llamado recursivo

# Uso de la función
def scraper_sciencedirect(url, sobrenombre):
    driver = initialize_driver()
    all_scraper = ""
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        
        keywords = load_keywords()
        all_scraper = recursive_scraper(driver, keywords, 0, all_scraper)
        
        # Guardar los resultados
        file_path = get_next_versioned_filename("ruta_guardado", "resultado")
        process_scraper_data(file_path, all_scraper)
        
    finally:
        driver.quit()