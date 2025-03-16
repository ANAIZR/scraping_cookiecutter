from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    save_to_mongo
)
import time
import random
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def scraper_euphresco(url, sobrenombre):
    logger = get_logger("EUPHRESCO SCR")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = driver_init()
    collection, fs = connect_to_mongo()
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    all_scraper = ""
    scraped_urls = set()
    failed_urls = set()
    visited_urls = set()
    object_ids = []
    
    domain = "https://drop.euphresco.net"
    
    try:
        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(7)

        logger.info("✅ Página cargada correctamente.")
        
        def extract_links():
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            results = soup.select("div#divsearch span.color")
            
            for result in results:
                links = result.select("a")
                for link in links:
                    href = link.get("href")
                    if href:
                        full_href = urljoin(domain, href)
                        if full_href not in visited_urls:
                            visited_urls.add(full_href)
                            scraped_urls.add(full_href)
                            nonlocal total_links_found
                            total_links_found += 1
                            logger.info(f"✅ Enlace agregado: {full_href}")
        
        extract_links()
        
        while True:
            try:
                more_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div#divmore button.btn.btn-success"))
                )
                more_button.click()
                time.sleep(5)  # Espera para cargar nuevos enlaces
                extract_links()
            except:
                logger.info("🔍 No hay más botones 'Ver más'. Terminando extracción de enlaces.")
                break
        
        logger.info(f"🔍 Se encontraron {total_links_found} enlaces en total.")
        
        for href in list(scraped_urls):
            try:
                logger.info(f"🔍 Procesando: {href}")
                
                driver.get(href)
                driver.execute_script("document.body.style.zoom='100%'")
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(5)
                
                try:
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.margin10:nth-child(5)"))
                    )
                    content_text = element.text.strip()
                    logger.info("✅ Encontrado: div.margin10:nth-child(5)")
                
                except:
                    logger.warning("⚠️ No encontrado: div.margin10:nth-child(5). Intentando div.row div.margin10")
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.row div.margin10"))
                    )
                    content_text = element.text.strip()
                    logger.info("✅ Encontrado: div.row div.margin10")
                
                if content_text:
                    object_id = save_to_mongo("urls_scraper", content_text, href, url)
                    total_scraped_successfully += 1
                    scraped_urls.append(href)
                    
                logger.info(f"✅ Contenido extraído de {href}")
                 
            except Exception as e:
                logger.error(f"No se pudo extraer contenido de {href}.")
                total_failed_scrapes += 1
                failed_urls.add(href)
        
        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre,)        
        return response 
                
    except Exception as e:
        logger.error(f"⚠️ Error general durante el scraping: {str(e)}")

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")