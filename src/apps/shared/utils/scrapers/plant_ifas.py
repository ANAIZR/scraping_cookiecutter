from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import urljoin
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    save_to_mongo
)
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("scraper")


def scraper_plant_ifas(url, sobrenombre):

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    all_scraper = ""  
    visited_urls = set()
    urls_not_scraped = []
    scraped_urls = []
    total_scraped_links = 0

    try:
        driver.get(url)
        logger.info(f"Accediendo a {url}")
        time.sleep(2)

        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#app section.plant-cards"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        content = soup.select_one("#app section.plant-cards")

        if content:
            cards = content.select("ul.plants li.plant")
            logger.info(f"Se encontraron {len(cards)} tarjetas de plantas.")
            all_scraper += f"Se encontraron {len(cards)} tarjetas de plantas.\n"

            for i, card in enumerate(cards, start=1):
                link_card_element = card.select_one("a")
                if link_card_element:
                    link_card = link_card_element.get("href")
                    if link_card:
                        page = urljoin(url, link_card)
                        if page in visited_urls:
                            continue

                        visited_urls.add(page)
                        logger.info(f"Procesando tarjeta {i}: {page}")
                        all_scraper += f"Procesando tarjeta {i}: {page}\n"

                        driver.get(page)
                        time.sleep(random.uniform(3, 5))  

                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "section.plant-page")
                            )
                        )

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        content_container = soup.select_one("div.content")

                        if content_container:
                            cleaned_text = " ".join(content_container.text.split())
                            object_id = save_to_mongo("urls_scraper", cleaned_text, page, url)  # 📌 Guardar en `urls_scraper`
                            total_scraped_links += 1
                            scraped_urls.append(page)
                            logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")
                            

                        else:
                            logger.warning(f"No se encontró contenido en {page}")
                            urls_not_scraped.append(page)

        else:
            logger.warning("No se encontró contenido en la sección de tarjetas de plantas.")

        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de URLs encontradas: {len(visited_urls)}\n"
            f"Total de URLs scrapeadas: {len(scraped_urls)}\n"
            f"Total de URLs no scrapeadas: {len(urls_not_scraped)}\n"
            f"Total de archivos almacenados en MongoDB: {total_scraped_links}\n\n"
            f"{'-'*80}\n\n"
        )

        if scraped_urls:
            all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"

        if urls_not_scraped:
            all_scraper += "URLs no scrapeadas:\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)        
        return response
     


    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
