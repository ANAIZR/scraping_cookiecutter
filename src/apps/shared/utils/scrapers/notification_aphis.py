from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework.response import Response
from rest_framework import status
import time
from bson import ObjectId
from datetime import datetime
from ..functions import (
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
    process_scraper_data_v2,
    initialize_driver,
    extract_text_from_pdf,
)

def scraper_notification_aphis(url, sobrenombre):
    logger = get_logger("NOTIFICATION APHIS")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    total_scraped_links = 0
    scraped_urls = []
    non_scraped_urls = []
    hrefs = [] #set() 

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
                object_id = fs.put(
                    body_text.encode("utf-8"),
                    source_url=href,
                    scraping_date=datetime.now(),
                    Etiquetas=["planta", "plaga"],
                    contenido=body_text,
                    url=url
                )
                total_scraped_links += 1
                scraped_urls.append(href)
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                if len(existing_versions) > 1:
                    oldest_version = existing_versions[-1]
                    fs.delete(ObjectId(oldest_version._id))
                    logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version._id}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error al procesar el enlace {url}: {e}")
            non_scraped_urls.append(href)  

        return new_links

    def scrape_pages_in_parallel(url_list):
        nonlocal total_scraped_links, non_scraped_urls
        new_links = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {
                executor.submit(scrape_page, url): (url)
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

    def extract_hrefs_from_url_main():
        driver = initialize_driver()
        driver.get(url)
        time.sleep(random.uniform(3, 6))
 

        while True:
            contents_div = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "DataTables_Table_0"))
                )
            logger.info("Se encontró el resultados.")

            if contents_div:
                tbody = contents_div.find_element(By.CSS_SELECTOR,"tbody")
                if tbody:
                    for row in tbody.find_elements(By.CSS_SELECTOR,"tr"):
                        tds = row.find_elements(By.CSS_SELECTOR,"td")
                        segundo_td = tds[1]  # Índice 1 para el segundo td
                        link = segundo_td.find_element(By.CSS_SELECTOR,"a").get_attribute("href")
                        if link:
                            hrefs.append(link)
                        
            else:
                logger.info("No se encontró el div#contents en la página principal.")

            try:
                next_button = driver.find_element(
                    By.CSS_SELECTOR,
                    "button.dt-paging-button.next",
                )
                if "disabled" in next_button.get_attribute("class"):
                    logger.info(
                        "No hay más páginas disponibles. Finalizando búsqueda para esta palabra clave."
                    )
                    break
                else:
                    logger.info(
                        f"Yendo a la siguiente página"
                    )
                    next_button.click()
                    time.sleep(random.uniform(1, 2))
            except Exception as e:
                logger.info(
                    "No se encontró el botón para la siguiente página."
                )
                break  

        driver.quit()
 
    try:
        extract_hrefs_from_url_main()
        logger.info(f"Total de enlaces encontrados: {len(hrefs)}")
        print("hrefs by quma: ",hrefs)

        new_links = scrape_pages_in_parallel(hrefs)

        all_scraper = (
            f"Total enlaces scrapeados: {total_scraped_links}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
