from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    connect_to_mongo,
    get_logger,
    driver_init,
    process_scraper_data,
    load_keywords
)
from rest_framework.response import Response
from rest_framework import status
import time
import random
from datetime import datetime
from bson import ObjectId
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

logger = get_logger("scraper")

def scraper_canada_ca(url, sobrenombre):
    driver = driver_init()
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 6))
        logger.info(f"Iniciando scraping para URL: {url}")

        collection, fs = connect_to_mongo()
        keywords = load_keywords("plants.txt")

        if not keywords:
            return Response(
                {"status": "error", "message": "El archivo de palabras clave está vacío o no se pudo cargar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Página de canada.ca cargada exitosamente.")

        all_scraper = ""
        total_scraped_successfully = 0
        total_failed_scrapes = 0
        scraped_urls = []
        failed_urls = []

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")

            try:
                driver.get(url)
                time.sleep(random.uniform(3, 6))

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#sch-inp-ac"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                
                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button#sch-inp"))
                )
                search_button.click()
                time.sleep(random.uniform(3, 6))
            except Exception as e:
                logger.error(f"Error al buscar la palabra clave: {keyword}. Error: {str(e)}")
                continue

            hrefs = set()
            total_urls_found = 0
            max_first_result = 20
            
            while True:
                try:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    links = soup.select("section#wb-land a[href]")

                    if not links:
                        logger.warning(f"No se encontraron enlaces en la búsqueda para '{keyword}'")
                        break

                    for link in links:
                        full_href = link.get("href")
                        if full_href and full_href.startswith("http"):
                            hrefs.add(full_href)
                            total_urls_found += 1

                    current_url = driver.current_url
                    first_result_value = int(current_url.split("firstResult=")[1].split("&")[0]) if "firstResult=" in current_url else 0

                    if first_result_value >= max_first_result:
                        logger.info(f"Se alcanzó el límite de paginación (firstResult={max_first_result}). Deteniendo el scraping.")
                        break

                    try:
                        time.sleep(2)
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.page-button.next-page-button"))
                        )
                        print("✅ Botón 'Next' encontrado, haciendo clic.")
                        driver.execute_script("arguments[0].click();", next_button)
                        logger.info(f"Se hizo clic en el botón 'Next'. Nueva URL: {driver.current_url}")
                        time.sleep(random.uniform(3, 6))
                    except (TimeoutException, NoSuchElementException):
                        print("❌ Botón 'Next' no encontrado, terminando la paginación.")
                        logger.info("No hay más páginas disponibles o no se encontró el botón 'Next'.")
                        break
                except Exception as e:
                    logger.error(f"Error al obtener los resultados de la búsqueda: {str(e)}")
                    break
            
            for href in hrefs:
                try:
                    driver.get(href)
                    time.sleep(random.uniform(3, 6))
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    content = soup.select_one("main.main-container")

                    if content:
                        content_text = content.text.strip()
                        object_id = fs.put(
                            content_text.encode("utf-8"),
                            source_url=href,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=content_text,
                            url=url
                        )
                        total_scraped_successfully += 1
                        scraped_urls.append(href)
                        
                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                        
                        existing_versions = list(
                            fs.find({"source_url": href}).sort("scraping_date", -1)
                        )
                        
                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(ObjectId(oldest_version["_id"]))
                            logger.info(f"Se eliminó la versión más antigua para {href} (object_id: {oldest_version['_id']})")

                    
                except Exception as e:
                    logger.error(f"Error al extraer contenido de {href}: {str(e)}")
                    total_failed_scrapes += 1
                    failed_urls.append(href)

        all_scraper += f"Total enlaces encontrados: {total_urls_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"
        
        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error en el scraper: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        driver.quit()
