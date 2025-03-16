from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from urllib.parse import urljoin
from rest_framework.response import Response
from rest_framework import status
import time
import requests
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    save_to_mongo
)

lock = Lock()

def fetch_content(href, logger, scraped_count, failed_hrefs, collection, fs, url):
    try:
        response = requests.get(href, timeout=10)
        logger.info(f"Accediendo al enlace: {href}")
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        inner_content = soup.find(id="inner-content")
        if inner_content:
            content_text = inner_content.get_text(strip=True)
            logger.info(
                f"Contenido obtenido del enlace: {href}, Longitud: {len(content_text)} caracteres"
            )
            with lock:
                scraped_count[0] += 1

            object_id = save_to_mongo("urls_scraper", content_text, href, url)  # 📌 Guardar en `urls_scraper`
            logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")

            
            
            return href
        else:
            logger.warning(f"No se encontró contenido interno en la página: {href}")
            failed_hrefs.append(href)
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al procesar el enlace {href}: {str(e)}")
        failed_hrefs.append(href)
        return None

def scraper_iucngisd(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo()
    all_scraper = ""
    scraped_count = [0]
    failed_hrefs = []
    scraped_urls = []

    try:
        driver = initialize_driver()
        driver.get(url)
        logger.info(f"Abriendo URL con Selenium: {url}")

        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "go"))
        )
        search_button.click()
        logger.info("Botón de búsqueda clicado con Selenium.")

        time.sleep(5)

        page_source = driver.page_source
        driver.quit()

        soup = BeautifulSoup(page_source, "html.parser")

        ul_tag = soup.select_one("ul.content.spec")
        if not ul_tag:
            raise Exception(
                "No se encontró el elemento ul con la clase 'content spec'."
            )

        hrefs = []
        li_tags = ul_tag.find_all("li")
        for li_tag in li_tags:
            a_tag = li_tag.find("a")
            if a_tag and a_tag.get("href"):
                hrefs.append(urljoin(url, a_tag["href"]))

        logger.info(f"Total de enlaces encontrados: {len(hrefs)}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(
                executor.map(
                    lambda href: fetch_content(
                        href, logger, scraped_count, failed_hrefs, collection, fs, url
                    ),
                    hrefs,
                )
            )

        scraped_urls = [res for res in results if res]

        all_scraper += (
            f"Total enlaces encontrados: {len(hrefs)}\n"
            f"Total enlaces scrapeados exitosamente: {scraped_count[0]}\n"
            f"Enlaces scrapeados:\n" + "\n".join(scraped_urls) + "\n"
            f"Total enlaces fallidos: {len(failed_hrefs)}\n"
            f"Enlaces fallidos:\n" + "\n".join(failed_hrefs) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)        
     
        return response


    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return Response(
            {"error": f"Unexpected error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
