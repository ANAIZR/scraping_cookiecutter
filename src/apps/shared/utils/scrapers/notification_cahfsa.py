from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    extract_text_from_pdf,
)
import time
import random
from datetime import datetime
from bson import ObjectId
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def scraper_cahfsa(url, sobrenombre):
    logger = get_logger("CAHFSA SCRAPER")
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

        sections = [
            {
                "div_selector": "div.section_wrapper.mfn-wrapper-for-wraps.mcb-section-inner.mcb-section-inner-e71c2ec93",
                "load_more_selector": "a.pager_load_more.button.has-icon"
            },
            {
                "div_selector": "div.section_wrapper.mfn-wrapper-for-wraps.mcb-section-inner.mcb-section-inner-ec0027c4e",
                "load_more_selector": ".section:nth-child(3) .pager_load_more:nth-child(1)"
            }
        ]
        
        for section in sections:
            div_selector = section["div_selector"]
            load_more_selector = section["load_more_selector"]

            try:
                for i in range(2):
                    try:
                        driver.execute_script("document.body.style.zoom='100%'")
                        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                        time.sleep(2)

                        load_more_button = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, load_more_selector))
                        )

                        driver.execute_script("arguments[0].click();", load_more_button)
                        logger.info(f"Load More clickeado ({i+1}) veces en {div_selector}")
                        time.sleep(random.uniform(3, 5))

                    except (TimeoutException, NoSuchElementException):
                        logger.info(f"No hay más 'Load More' en {div_selector}")
                        break

                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                section_div = soup.select_one(div_selector)

                if section_div:
                    links = section_div.find_all("a", href=True)
                    for link in links:
                        href = link["href"]
                        if href not in scraped_urls and href not in failed_urls:
                            scraped_urls.add(href)
                            total_links_found += 1
                        else:
                            failed_urls.add(href)
                            total_failed_scrapes += 1
                            total_links_found += 1
                else:
                    logger.warning(f"No se encontró la sección {div_selector}")

            except Exception as e:
                logger.error(f"Error en la sección {div_selector}: {e}")
        
        for href in scraped_urls:
            try:
                if href.endswith(".pdf"):
                    logger.info(f"Extrayendo texto de {href}")
                    content_text = extract_text_from_pdf(href)
                else:
                    driver.get(href)
                    driver.execute_script("document.body.style.zoom='100%'")
                    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                    time.sleep(5)

                    try:
                        content_element = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.mcb-background-overlay"))
                        )
                        content_text = content_element.text.strip()
                    except TimeoutException:
                        content_element = driver.find_element(By.TAG_NAME, "section.mcb-section.the_content.has_content")
                        content_text = content_element.text.strip()

                    soup = BeautifulSoup(content_text, "html.parser")
                    for img in soup.find_all("img"):
                        img.decompose()
                    content_text = soup.get_text()

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
                        fs.delete(oldest_version._id)  
                        logger.info(f"Se eliminó la versión más antigua: '{href}' object_id: {oldest_version['_id']}")

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
