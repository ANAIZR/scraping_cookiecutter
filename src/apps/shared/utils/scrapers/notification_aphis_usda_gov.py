from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    load_keywords,
    extract_text_from_pdf,
)
import time
import random
from datetime import datetime
from bson import ObjectId
from urllib.parse import urljoin, urlparse, parse_qs
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

def scraper_aphis_usda_gov(url, sobrenombre):
    logger = get_logger("APHIS USDA GOV")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    all_scraper = ""
    scraped_urls = set()
    failed_urls = set()
    visited_urls = set() 
    object_ids = []

    try:
        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)

        logger.info("✅ Página cargada correctamente.")

        while True:
            current_url = driver.current_url
            parsed_url = urlparse(current_url)
            query_params = parse_qs(parsed_url.query)
            current_page = int(query_params.get("page", [1])[0]) 

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            article_divs = soup.select("div.article.c-view__row")

            if not article_divs:
                logger.warning("⚠️ No se encontraron artículos en la página.")

            for article in article_divs:
                link = article.select_one("a[href]")
                if link and link["href"]:
                    href = urljoin(url, link["href"])
                    
                    if href not in visited_urls: 
                        visited_urls.add(href)
                        scraped_urls.add(href)
                        total_links_found += 1
                        print(f"✅ Enlace agregado: {href}") 
                        logger.info(f"✅ Enlace agregado: {href}")

            if current_page >= 2:
                logger.info("🚀 Se alcanzó page=2. Deteniendo la paginación.")
                break

            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "li.c-pager__item--next a.c-pager__link--next")
                logger.info(f"✅ Se encontró el botón 'Next'. Pasando a la siguiente página...")
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(random.uniform(5, 10))
            except (TimeoutException, NoSuchElementException):
                logger.info("No se encontró el botón 'Next' o no hay más páginas disponibles.")
                break

        for href in scraped_urls.copy():
            try:
                driver.get(href)
                driver.execute_script("document.body.style.zoom='100%'")
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(5)

                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.c-field--name-body"))
                )
                time.sleep(random.randint(2, 4))
                content_text = driver.find_element(By.CSS_SELECTOR, "div.c-field--name-body").text.strip()

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
                    logger.info(f"📂 Archivo almacenado en MongoDB con object_id: {object_id}")

                    existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))

                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        file_id = oldest_version._id
                        fs.delete(file_id)
                        logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")

            except Exception as e:
                logger.error(f"❌ No se pudo extraer contenido de {href}: {e}")
                total_failed_scrapes += 1
                failed_urls.add(href)
            finally:
                driver.get(url)

        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"⚠️ Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("🚪 Navegador cerrado.")