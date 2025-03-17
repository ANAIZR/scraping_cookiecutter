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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def scraper_notification_ippc(url, sobrenombre):
    logger = get_logger("IPPC INT")
    logger.info(f"Iniciando scraping para URL: {url}")
    
    driver = driver_init()
    db, fs = connect_to_mongo() 
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

        logger.info("Página cargada correctamente.")
        domain = "https://www.ippc.int"

        while True:
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            results_divs = soup.select("tbody tr.odd td:first-child a, tbody tr.even td:first-child a")

            for link in results_divs:
                href = urljoin(domain, link["href"])

                if href not in visited_urls:
                    visited_urls.add(href)
                    scraped_urls.add(href)
                    total_links_found += 1
                    print(f"✅ Enlace agregado: {href}")

            next_button_soup = soup.select_one("li.c-pager__item--next a.c-pager__link--next")

            if not next_button_soup:
                logger.info("No se encontró el botón 'Next' en el HTML. Terminando la paginación.")
                break

            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "li.c-pager__item--next a.c-pager__link--next"))
                )
                driver.execute_script("arguments[0].click();", next_button)
                logger.info("Clic en 'Next' realizado correctamente.")
                time.sleep(random.uniform(5, 10))

            except (TimeoutException, NoSuchElementException) as e:
                logger.warning(f"No se pudo hacer clic en 'Next': {e}")
                break  

        for href in scraped_urls.copy():
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
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div#divmainbox"))
                    )
                    time.sleep(random.randint(2, 4))
                    content_text = driver.find_element(By.CSS_SELECTOR, "div#divmainbox").text.strip()

                if content_text:
                    object_id = save_to_mongo("news_articles", content_text, href, url)
                    object_ids.append(object_id)
                    total_scraped_successfully += 1
                    logger.info(f"📂 Noticia guardada en `news_articles` con object_id: {object_id}")

            except Exception as e:
                logger.error(f"No se pudo extraer contenido de {href}. Error: {e}")
                total_failed_scrapes += 1
                failed_urls.add(href)
                scraped_urls.remove(href)

        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre,"news_articles")        
     
        return response


    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
