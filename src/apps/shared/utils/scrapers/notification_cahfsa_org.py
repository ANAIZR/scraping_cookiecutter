from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    extract_text_from_pdf,
    save_to_mongo
)
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup

def scraper_notification_cahfsa_org(url, sobrenombre):
    logger = get_logger("CAHFSA ORG")
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
    total_links_found = 0
    object_ids = []

    try:
        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)

        logger.info("✅ Página cargada correctamente.")

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        results = soup.select("div.column_attr.mfn-inline-editor li")      

        for result in results:
            links = result.select("a")
            
            for link in links:
                href = link.get("href")

                if href and href not in visited_urls:
                    visited_urls.add(href)
                    scraped_urls.add(href)
                    total_links_found += 1
                    logger.info(f"✅ Enlace agregado: {href}")

        logger.info(f"🔍 Se encontraron {total_links_found} enlaces en total.")

        for href in scraped_urls.copy():
            try:
                logger.info(f"🔍 Procesando: {href}")

                if href.endswith(".pdf"):
                    logger.info(f"📄 Extrayendo texto de PDF: {href}")
                    content_text = extract_text_from_pdf(href)
                else:
                    driver.get(href)
                    driver.execute_script("document.body.style.zoom='100%'")
                    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                    time.sleep(5)

                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li"))
                    )
                    time.sleep(random.randint(2, 4))
                    content_text = driver.find_element(By.CSS_SELECTOR, "li").text.strip()
                
                if content_text:
                    object_id = save_to_mongo("news_articles", content_text, href, url)
                    total_scraped_successfully +=1
                    logger.info(f"📂 Noticia guardada en `news_articles` con object_id: {object_id}")
                    
                    

                logger.info(f"✅ Contenido extraído de {href}")

            except Exception as e:
                logger.error(f"No se pudo extraer contenido de {href}.")
                total_failed_scrapes += 1
                failed_urls.add(href)
                scraped_urls.remove(href)
        
        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre,collection)
        return response 

    except Exception as e:
        logger.error(f"⚠️ Error general durante el scraping: {str(e)}")

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")