from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    load_keywords,
    extract_text_from_pdf,
)
import time
import random
from datetime import datetime
from bson import ObjectId
from urllib.parse import urljoin
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

def scraper_aphis_usda_gov (url, sobrenombre):
    logger = get_logger("APHIS USDA GOV")
    logger.info(f"Iniciando scraping para URL: {url}")
    
    driver = driver_init()
    collection, fs = connect_to_mongo()
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    all_scraper = ""
    scraped_urls = set()
    failed_urls = set()
    object_ids = []
    
    try:
        driver.get(url)
        
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)
        
        logger.info("Página cargada correctamente.")
        
        while True:
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            results_divs = soup.find_all("div.c-article-list-search")
            
            for div in results_divs:
                link = div.find("a", href=True)
                if link and link["href"]:
                    href = link["href"]
                    if href not in scraped_urls and href not in failed_urls:
                        scraped_urls.add(href)
                        total_links_found += 1
                    else:
                        failed_urls.add(href)
                        total_failed_scrapes += 1
                        total_links_found += 1
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "li.c-pager__item--next a.c-pager__link--next")
                print(f"✅ Se encontró el botón 'Next'.")
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(random.uniform(5, 10))
            except (TimeoutException, NoSuchElementException):
                logger.info("No se encontró el botón 'Next' o no hay más páginas disponibles.")
                break
            
        for href in scraped_urls:
            try:
                if href.endswith(".pdf"):
                    logger.info(f"***Extrayendo texto de {href}")
                    content_text = extract_text_from_pdf(href)
                else:
                    driver.get(href)
                    
                    driver.execute_script("document.body.style.zoom='100%'")
                    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                    time.sleep(5)
                    
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article.is-promoted"))
                    )
                    time.sleep(random.randint(2, 4))
                    content_text = driver.find_element(By.CSS_SELECTOR, "article.is-promoted").text.strip()
                        
                if content_text and content_text.strip():
                    object_id = fs.put(
                        content_text.encode("utf-8"),
                         source_url=href,
                        scraping_date=datetime.now(),
                         Etiquetas=["planta", "plaga"],
                         contenido=content_text,
                         url=url
                    )
                    
                    object_ids.append(object_id)
                    total_scraped_successfully += 1

                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                    existing_versions = list(
                        fs.find({"source_url": href}).sort("scraping_date", -1)
                    )

                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        file_id = oldest_version._id 
                        fs.delete(file_id)  
                        logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                            
                    logger.info(f"Contenido extraído de {href}.")
            except Exception as e:
                logger.error(f"No se pudo extraer contenido de {href}: {e}")
                total_failed_scrapes += 1
                failed_urls.add(href)
            finally:
                driver.get(url)
                
        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
    
    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")