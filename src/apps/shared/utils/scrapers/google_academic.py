from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    connect_to_mongo,
    get_logger,
    driver_init,
    extract_text_from_pdf,
    load_keywords,
    process_scraper_data,
    save_to_mongo
)
from rest_framework.response import Response
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from rest_framework import status
import time
import random
from datetime import datetime
from bson import ObjectId
from bs4 import BeautifulSoup
import requests
import re

logger = get_logger("scraper")

def scraper_google_academic(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = driver_init()
    collection, fs = connect_to_mongo()

    keywords = load_keywords("plants.txt")
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    scraped_urls = []
    failed_urls = []

    try:
        for keyword in keywords:
            if not isinstance(keyword, str):
                logger.warning(f"La palabra clave no es una cadena válida: {keyword}")
                continue

            driver.get(url)
            logger.info(f"Procesando palabra clave: {keyword}")

            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#gs_hdr_tsi"))
            )
            search_box.clear()
            search_box.send_keys(keyword)
            time.sleep(random.uniform(2, 5))
            search_box.submit()
            time.sleep(random.uniform(2, 5))

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#gs_res_ccl_mid"))
            )

            visited_urls = set()
            while True:
                current_page_url = driver.current_url
                soup = BeautifulSoup(driver.page_source, "html.parser")
                links = soup.select("div.gs_ri h3 a")
                total_links_found += len(links)

                for link in links:
                    full_url = link.get("href")

                    if full_url not in visited_urls:
                        try:
                            if full_url.endswith(".pdf") or "/download" in full_url:
                                logger.info(f"***Extrayendo texto de {full_url}")
                                content_text = extract_text_from_pdf(full_url)
                            else:
                                driver.get(full_url)
                                time.sleep(2)
                                body_element = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                                )
                                content_text = body_element.text.strip() if body_element else ""

                            if content_text and not content_text.lower().startswith("error al extraer contenido del pdf"):

                                object_id = save_to_mongo("urls_scraper", content_text, full_url, url)
                                total_scraped_links += 1
                                scraped_urls.append(full_url)
                                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                

                            else:
                                total_failed_scrapes += 1
                                failed_urls.append(full_url)
                                logger.warning(f"Contenido fallido en {full_url}: {content_text}")

                        except Exception as e:
                            logger.error(f"No se pudo acceder al link {full_url}: {e}")
                            total_failed_scrapes += 1
                            failed_urls.append(full_url)

                        visited_urls.add(full_url)
                        if not (full_url.endswith(".pdf") or "/download" in full_url):
                            driver.back()
                            time.sleep(3)

                if "start=10" in current_page_url:
                    logger.info(f"Se alcanzó la página 10 para '{keyword}'. Fin del scraping para esta palabra.")
                    break

                try:
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div#gs_n td:nth-child(12) b"))
                    )
                    logger.info("✅ Botón 'Next' encontrado, haciendo clic.")
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(2)
                except (TimeoutException, NoSuchElementException):
                    logger.info("❌ Botón 'Next' no encontrado, terminando la paginación.")
                    break

        all_scraper = (
            f"Total enlaces encontrados: {total_links_found}\n"
            f"Total scrapeados con éxito: {total_scraped_successfully}\n"
            "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
            f"Total fallidos: {total_failed_scrapes}\n"
            "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
