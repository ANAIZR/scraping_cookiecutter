from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, InvalidArgumentException
from rest_framework.response import Response
from rest_framework import status
from bson.objectid import ObjectId
from datetime import datetime
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    save_to_mongo
)

def scraper_nematode(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    
    driver = driver_init()
    collection, fs = connect_to_mongo()
    domain = "https://nematode.ars.usda.gov"

    all_scraper = ""
    total_records_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    total_links_found = 0
    collected_urls = set()  
    scraped_urls = set()  
    failed_urls = set()  

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)

        current_page = 1  

        while current_page <= 2:  
            print(f"📌 Scrapeando página {current_page}...")
            logger.info(f"📌 Scrapeando página {current_page}...")

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            
            rows = soup.select("div.views-row")
            total_records_found += len(rows)

            for row in rows:
                link = row.select_one("a")
                if link and link.get("href"):
                    full_link = urljoin(domain, link["href"])

                    if full_link not in collected_urls:  
                        collected_urls.add(full_link)
                        total_links_found += 1

            
            if current_page == 1:
                try:
                    next_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[title='Go to next page']"))
                    )
                    driver.execute_script("arguments[0].click();", next_button)
                    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                    time.sleep(5)
                    current_page += 1  
                except Exception:
                    break  

            else:
                break  

        print(f"🔎 Total de URLs recolectadas: {len(collected_urls)}")
        logger.info(f"🔎 Total de URLs recolectadas: {len(collected_urls)}")

        
        for link in collected_urls:
            print(f"🌍 Scrapeando URL: {link}")
            logger.info(f"🌍 Scrapeando URL: {link}")

            try:
                driver.get(link)
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(5)

                page_source = driver.page_source
                page_soup = BeautifulSoup(page_source, "html.parser")
                page_text = page_soup.body.text.strip()
                
                if page_text:
                    object_id = save_to_mongo("urls_scraper", page_text, link, url)  # 📌 Guardar en `urls_scraper`
                    total_scraped_successfully += 1
                    scraped_urls.add(link) 
                    logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")
                    
            except Exception as e:
                logger.error(f"❌ Error en la URL {link}: {e}")

                
                if link not in scraped_urls:
                    failed_urls.add(link)
                    total_failed_scrapes += 1

        
        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre,collection)
        return response
    
    except Exception as e:
        return Response({"error": f"Ocurrió un error durante el scraping: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        driver.quit()
        logger.info("✅ Navegador cerrado.")
