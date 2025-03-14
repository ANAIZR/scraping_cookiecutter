from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import random
from datetime import datetime
from ..functions import (
    driver_init,
    get_logger,
    connect_to_mongo,
    get_random_user_agent,
    extract_text_from_pdf,
    process_scraper_data,
    save_to_mongo
)
from rest_framework.response import Response
from rest_framework import status
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

logger = get_logger("scraper")

def scraper_ippc_int(url, sobrenombre):
    logger = get_logger("IPPC INT")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo()
    total_scraped_links = 0
    scraped_urls = []
    non_scraped_urls = []
    hrefs = []  # Aquí se almacenarán todos los enlaces encontrados

    def scrape_page(href):
        nonlocal total_scraped_links, non_scraped_urls
        logger.info(f"Accediendo a {href}")

        headers = {"User-Agent": get_random_user_agent()}
        new_links = []

        try:
            response = requests.get(href, headers=headers)
            response.raise_for_status()

            logger.info(f"Extrayendo texto de PDF: {href}")
            body_text = extract_text_from_pdf(href)

            if body_text:
                object_id = save_to_mongo("urls_scraper", body_text, href, url)  # 📌 Guardar en `urls_scraper`
                scraped_urls.append(href)
                logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")
                

        except requests.exceptions.RequestException as e:
            logger.error(f"Error al procesar el enlace {href}: {e}")
            non_scraped_urls.append(href)

        return new_links

    def extract_hrefs_from_url_main():
        driver = driver_init()
        driver.get(url)
        time.sleep(random.uniform(3, 6))

        while True:
            select_element = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select.form-select.form-select-sm"))
            )
            dropdown = Select(select_element)
            dropdown.select_by_index(3)

            contents_div = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "publications"))
            )

            logger.info("Se encontró el resultados.")

            if contents_div:
                items = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "tr.odd, tr.even")
                    )
                )
                if items:
                    for item in items:
                        try:
                            href = item.find_element(By.CSS_SELECTOR, "tbody tr td a").get_attribute("href")
                        except NoSuchElementException:
                            href = None
                            logger.info("Elemento no encontrado, continuando...")
                        if href:
                            logger.info("URL encontrada, agregando...")
                            hrefs.append(href)
            else:
                logger.info("No se encontró el div#publications en la página principal.")

            try:
                next_page_button = driver.find_element(
                    By.ID,
                    "publications_next",
                )
                if "disabled" in next_page_button.get_attribute("class"):
                    logger.info("No hay más páginas disponibles. Finalizando búsqueda para esta página.")
                    break
                else:
                    logger.info("Yendo a la siguiente página")
                    next_page_button.click()
                    time.sleep(random.uniform(1, 2))
            except Exception as e:
                logger.info("No se encontró el botón para la siguiente página.")
                break

        driver.quit()

    def scrape_pages_in_parallel(url_list):
        nonlocal total_scraped_links, non_scraped_urls
        new_links = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {
                executor.submit(scrape_page, url): url
                for url in url_list
            }
            for future in as_completed(future_to_url):
                try:
                    result_links = future.result()
                    new_links.extend(result_links)
                except Exception as e:
                    logger.error(f"Error en tarea de scraping: {str(e)}")
                    non_scraped_urls.append(future_to_url)
        return new_links

    try:
        extract_hrefs_from_url_main()
        logger.info(f"Total de enlaces encontrados: {len(hrefs)}")

        new_links = scrape_pages_in_parallel(hrefs)

        total_links_found = len(hrefs)
        total_scraped_successfully = total_scraped_links
        total_failed_scrapes = len(non_scraped_urls)

        all_scraper = ""
        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(non_scraped_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
