from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    load_keywords,
    save_to_mongo 
)
from rest_framework.response import Response
import time
import random
from datetime import datetime
from urllib.parse import urljoin
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

def scraper_biblioteca_sibe(url, sobrenombre):
    logger = get_logger("BIBLIOTECA_SIBE")
    logger.info(f"Iniciando scraping para URL: {url}")
    
    driver = driver_init()
    db, fs = connect_to_mongo()  
    
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    all_scraper = ""
    
    domain = "https://biblioteca.ecosur.mx/"
    
    scraped_urls = set()
    failed_urls = set()

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(3)
        logger.info("Página principal cargada correctamente.")
        
        keywords = load_keywords("plants.txt")
        
        for keyword in keywords:
            try:
                search_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input.form-control"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                
                search_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button.btn.btn-secondary"))
                )
                
                search_button.click()
                time.sleep(random.uniform(3, 6))
                logger.info(f"✅ Se realizó la búsqueda con la palabra clave: '{keyword}'")
                
                while True:
                    try:
                        results_div = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div#userresults"))
                        )
                        logger.info(f"🔎 Se encontró 'div#userresults' para '{keyword}'")
                        
                        searchresults_links = results_div.find_elements(By.CSS_SELECTOR, "div.searchresults a.title")
                        
                        for link in searchresults_links:
                            href = link.get_attribute("href")
                            if not href.startswith("http"):
                                href = urljoin(domain, href)
                            
                            if href not in scraped_urls:
                                scraped_urls.add(href)
                                total_links_found += 1
                                logger.info(f"🌐 Enlace encontrado: {href}")
                    
                    except TimeoutException:
                        logger.warning(f"No se encontró el div#userresults para '{keyword}'")
                        break
                    
                    try:
                        next_button = driver.find_element(
                            By.CSS_SELECTOR,
                            'a.page-link[aria-label="Ir a la página siguiente"]'
                        )
                        logger.info("➡️ Se encontró botón 'Siguiente'. Pasando a la siguiente página.")
                        next_button.click()
                        time.sleep(random.uniform(3, 6))
                        
                    except NoSuchElementException:
                        logger.info("No hay más páginas para esta búsqueda.")
                        break
                
                driver.get(url)
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(3)
                
            except Exception as e:
                logger.warning(f"Error durante la búsqueda con palabra clave '{keyword}': {e}")
                continue
        
        for href in scraped_urls:
            try:
                driver.get(href)
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(2)
                
                logger.info(f"🟢 Entrando a {href} para extraer información.")
                
                content_text = ""
                
                try:
                    descriptions_div = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div#descriptions.ui-tabs-panel"))
                    )
                    content_text = descriptions_div.text.strip()
                    logger.info("✅ Se encontró div#descriptions.ui-tabs-panel sin hacer clic.")
                
                except TimeoutException:
                    logger.info("⏳ No se encontró div#descriptions.ui-tabs-panel, intentando hacer clic en 'a#ui-id-2.ui-tabs-anchor'.")
                    try:
                        notes_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a#ui-id-2.ui-tabs-anchor"))
                        )
                        notes_button.click()
                        time.sleep(random.uniform(2, 4))
                        descriptions_div = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div#descriptions.ui-tabs-panel"))
                        )
                        content_text = descriptions_div.text.strip()
                        logger.info("✅ Se encontró div#descriptions.ui-tabs-panel después de hacer clic.")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo hacer clic en la pestaña o no se encontró el div tras el clic.")
                
                if not content_text:
                    logger.info("🔎 Buscando div.record como último recurso.")
                    try:
                        catalogue_biblio_div = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.record"))
                        )
                        content_text = catalogue_biblio_div.text.strip()
                        logger.info("✅ Se encontró div.record.")
                    except TimeoutException:
                        logger.warning("⚠️ No se encontró div.record como último recurso.")
                
                if content_text:
                    object_id = save_to_mongo("urls_scraper", content_text, href, url)  # 📌 Guardar en `urls_scraper`
                    total_scraped_successfully += 1
                    logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")
                else:
                    logger.warning(f"❌ Contenido vacío o no disponible en {href}.")
                
            except Exception as e:
                logger.warning(f"Error extrayendo información de {href}: {e}")
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
        logger.error(f"Error al cargar la página principal: {e}")
        return Response({"error": str(e)}, status=500)
        
    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
