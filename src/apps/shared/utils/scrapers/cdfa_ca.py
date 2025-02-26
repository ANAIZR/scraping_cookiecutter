from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    load_keywords,
    extract_text_from_pdf
)
import time
import random
from datetime import datetime
from bson import ObjectId
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

def scraper_cdfa(url, sobrenombre):
    logger = get_logger("CDFA_CA")
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

        keywords = load_keywords("pruebas.txt")

        for keyword in keywords:
            try:
                search_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input.search-textfield"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                
                try:
                    search_button = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "button.gsc-search-button"))
                    )
                    logger.info("✅ Se encontró el botón de búsqueda con Selenium")
                except TimeoutException:
                    logger.error("❌ No se encontró el botón con Selenium después de la espera")
                    continue
                
                try:
                    search_button.click()
                except:
                    driver.execute_script("arguments[0].click();", search_button)
                
                time.sleep(random.uniform(3, 6))

                while True:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    results_divs = soup.select("div.gsc-webResult.gsc-result")

                    for div in results_divs:
                        link = div.find("a", href=True)
                        if link and link["href"]:
                            href = link["href"]
                            if href not in scraped_urls and href not in failed_urls:
                                scraped_urls.add(href)
                                total_links_found += 1

                    try:
                        pagination = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.gsc-cursor"))
                        )
                        pages = driver.find_elements(By.CSS_SELECTOR, "div.gsc-cursor-page")

                        current_page = driver.find_element(By.CSS_SELECTOR, "div.gsc-cursor-current-page").text.strip()
                        next_page = None

                        for page in pages:
                            page_number = page.text.strip()
                            if page_number.isdigit() and int(page_number) > int(current_page):
                                next_page = page
                                break

                        if next_page:
                            logger.info(f"📄 Pasando a la página {next_page.text}...")
                            driver.execute_script("arguments[0].scrollIntoView();", next_page)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", next_page)
                            time.sleep(random.uniform(3, 6))

                            WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                            time.sleep(3)
                        else:
                            logger.info("🚫 No hay más páginas disponibles.")
                            break

                    except TimeoutException:
                        logger.info("🚫 No se encontró la paginación.")
                        break

                logger.info(f"🔍 Comenzando a procesar {len(scraped_urls)} enlaces almacenados.")
                
                for href in scraped_urls:
                    try:
                        if href.endswith(".pdf"):
                            logger.info(f"📄 Extrayendo texto de PDF: {href}")
                            content_text = extract_text_from_pdf(href)
                        else:
                            driver.get(href)
                            
                            driver.execute_script("document.body.style.zoom='100%'")
                            WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                            time.sleep(5)

                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.region-content"))
                            )
                            time.sleep(random.randint(2, 4))
                            content_text = driver.find_element(By.CSS_SELECTOR, "div.region-content").text.strip()

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

            except Exception as e:
                logger.warning(f"Error durante la búsqueda con palabra clave '{keyword}': {e}")
                continue

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
