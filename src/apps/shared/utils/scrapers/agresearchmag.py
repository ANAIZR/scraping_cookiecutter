from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    extract_text_from_pdf,
)
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

logger = get_logger("scraper")

def scraper_agresearchmag(url, sobrenombre):
    driver = driver_init()
    domain = "https://agresearchmag.ars.usda.gov"
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    scraped_urls = set()
    failed_urls = set()
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

        li_elements = panel.find_elements(By.CSS_SELECTOR, "li.als-item")
        
        for li in li_elements:
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(li)).click()
                time.sleep(random.uniform(3, 5))

                text_center_divs = driver.find_elements(By.CSS_SELECTOR, "div.text-center a")
                for link in text_center_divs:
                    href = link.get_attribute("href")
                    if href and href not in scraped_urls:
                        fullhref = domain + href if not href.startswith("http") else href
                        scraped_urls.add(fullhref)
                        total_links_found += 1
                        logger.info(f"Enlace extraído: {fullhref}")
            except (ElementClickInterceptedException, TimeoutException) as e:
                logger.error(f"No se pudo hacer clic en un elemento: {str(e)}")
                break

        for href in scraped_urls:
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
                    object_ids.append(object_id)
                    total_scraped_successfully += 1

                    logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version.id}")
                    
                    existing_versions = list(
                        fs.find({"source_url": href}).sort("scraping_date", -1)
                    )

                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        file_id = oldest_version._id  
                        fs.delete(file_id)  
                        logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")  # Log correcto

                            
            except Exception as e:
                logger.error(f"No se pudo extraer contenido de {href}: {e}")
                total_failed_scrapes += 1
                failed_urls.add(href)

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