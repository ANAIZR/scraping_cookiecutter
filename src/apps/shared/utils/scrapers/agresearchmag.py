from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    extract_text_from_pdf,
)
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException

logger = get_logger("scraper")

def scraper_agresearchmag(url, sobrenombre):
    driver = driver_init()
    domain = "https://agresearchmag.ars.usda.gov"
    
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    
    scraped_urls = set()
    failed_urls = set()
    visited_urls = set()  
    object_ids = []
    all_scraper = ""

    try:
        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)

        logger.info(f"Iniciando scraping para URL: {url}")

        collection, fs = connect_to_mongo()

        panel = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.panel-body ul.als-wrapper"))
        )

        next_button_selector = "span.als-next"
        max_attempts = 10
        attempts = 0
        last_index = 0

        while attempts < max_attempts:
            li_elements = panel.find_elements(By.CSS_SELECTOR, "li.als-item")
            
            if not li_elements:
                logger.warning("No se encontraron elementos <li>. Saliendo del bucle.")
                break

            for index in range(last_index, len(li_elements)):
                try:
                    li = li_elements[index]
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(li)).click()
                    time.sleep(random.uniform(3, 5))

                    active_class = li.get_attribute("class")
                    if "active" in active_class:
                        logger.info(f"Elemento {index+1} activado correctamente.")

                        text_center_divs = driver.find_elements(By.CSS_SELECTOR, "div.text-center a")
                        for link in text_center_divs:
                            href = link.get_attribute("href")
                            if href and href not in visited_urls:
                                fullhref = domain + href if not href.startswith("http") else href
                                scraped_urls.add(fullhref)
                                visited_urls.add(fullhref) 
                                total_links_found += 1
                                logger.info(f"Enlace extraído: {fullhref}")
                    else:
                        logger.warning(f"Elemento {index+1} no se activó correctamente.")
                except (ElementClickInterceptedException, TimeoutException) as e:
                    logger.error(f"No se pudo hacer clic en el elemento {index+1}: {str(e)}")
                    last_index = index
                    break
            
            try:
                driver.execute_script("document.body.style.zoom='100%'")
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(5)
                
                next_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, next_button_selector)))
                next_button.click()
                logger.info("Clic en 'siguiente' realizado. Cargando más elementos...")
                time.sleep(random.uniform(4, 6))
                attempts += 1
                last_index += 1
            except (TimeoutException, NoSuchElementException):
                logger.info("No se encontró el botón 'siguiente' o ya no hay más elementos. Terminando.")
                break

        additional_scraped_urls = set()
        
        for href in scraped_urls:
            try:
                driver.get(href)
                driver.execute_script("document.body.style.zoom='100%'")
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(5)

                panel_body = driver.find_elements(By.CSS_SELECTOR, "div.panel-body div.row div.panel-body a")
                for link in panel_body:
                    inner_href = link.get_attribute("href")
                    if inner_href and inner_href not in visited_urls:
                        full_inner_href = urljoin(domain, inner_href)
                        additional_scraped_urls.add(full_inner_href)
                        visited_urls.add(full_inner_href)
                        logger.info(f"Enlace extraído dentro de la página: {full_inner_href}")
            except Exception as e:
                logger.error(f"No se pudo extraer enlaces adicionales de {href}: {e}")

        scraped_urls.update(additional_scraped_urls)

        for href in scraped_urls.copy():
            try:
                driver.get(href)
                driver.execute_script("document.body.style.zoom='100%'")
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(5)

                try:
                    third_row = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.row:nth-of-type(3)"))
                    )
                    content_text = third_row.text.strip()
                    logger.info(f"Extraído div.row:nth-of-type(3) de {href}")
                except TimeoutException:
                    content_text = driver.find_element(By.TAG_NAME, "body").text.strip()
                    logger.info(f"No se encontró div.row:nth-of-type(3), extrayendo body de {href}")

                if content_text:
                    object_id = fs.put(
                        content_text.encode("utf-8"),
                        source_url=href,
                        scraping_date=datetime.now(),
                        Etiquetas=["planta", "plaga"],
                        contenido=content_text,
                        url=url
                    )
                    existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                 
                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        file_id = oldest_version._id  
                        fs.delete(file_id)  
                        logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                    object_ids.append(object_id)
                    total_scraped_successfully += 1
                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                else:
                    raise Exception("Contenido vacío o no extraído correctamente")

            except Exception as e:
                logger.error(f"No se pudo extraer contenido de {href}: {e}")
                total_failed_scrapes += 1
                failed_urls.add(href)
                scraped_urls.remove(href) 

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