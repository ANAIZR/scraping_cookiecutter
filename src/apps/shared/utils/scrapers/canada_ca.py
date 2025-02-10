from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    get_next_versioned_pdf_filename,
    process_scraper_data,
    load_keywords
)
from rest_framework.response import Response
from rest_framework import status
import os
from datetime import datetime
import random
import json
import time
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from django.utils.timezone import make_aware

logger = get_logger("scraper")

def scraper_canada_ca(url, sobrenombre):
    driver = initialize_driver()
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 6))
        logger.info(f"Iniciando scraping para URL: {url}")
        collection, fs = connect_to_mongo()
        main_folder = generate_directory(sobrenombre)

        keywords = load_keywords("plants.txt")
        if not keywords:
            return Response(
                {
                    "status": "error",
                    "message": "El archivo de palabras clave está vacío o no se pudo cargar.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        logger.infoº("Página de canada.ca cargada exitosamente.")

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
            
            keyword_folder = generate_directory(keyword, main_folder)
            keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)

            content_accumulated = ""

            while True:
                try:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    results = soup.select("section#wb-land")

                    # Extraer enlaces de los resultados de búsqueda
                    for div in results:
                        link = div.find("a", href=True)
                        if link and link["href"]:
                            full_href = link["href"]
                            hrefs.append(full_href)
                            total_urls_found += 1

                    # Extraer información de cada URL encontrada
                    for href in hrefs:
                        try:
                            driver.get(href)
                            time.sleep(random.uniform(3, 6))

                            page_source = driver.page_source
                            soup = BeautifulSoup(page_source, "html.parser")

                            # Extraer el contenido del selector main.main-container
                            main_content = soup.select_one("main.main-container")
                            text_content = main_content.get_text(strip=True) if main_content else "No se encontró contenido"

                            content_accumulated += f"URL: {href}\nContenido:\n{text_content}\n\n"
                            content_accumulated += "-" * 100 + "\n\n"

                        except Exception as e:
                            logger.error(f"Error al extraer contenido de {href}: {str(e)}")
                            continue

                    # Manejo de paginación
                    try:
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.page-button"))
                        )
                        next_page_url = next_button.get_attribute("href")
                        
                        if "firstResult=" in next_page_url:
                            next_page_number = int(next_page_url.split("firstResult=")[1].split("&")[0])
                        else:
                            next_page_number = 10

                        if next_page_number >= 10:
                            logger.info(f"Se ha alcanzado el límite de paginación (firstResult=10). Deteniendo el scraping.")
                            break

                        next_button.click()
                        time.sleep(random.uniform(3, 6))
                    except (TimeoutException, NoSuchElementException):
                        logger.info("No hay más páginas disponibles.")
                        break 

                except Exception as e:
                    logger.error(f"Error al obtener los resultados de la búsqueda: {str(e)}")
                    break
    except Exxception as e:
        logger.error(f"Error al cargar la página de canada.ca: {str(e)}")
        return Response(
            {
                "status": "error",
                "message": f"Error al cargar la página de canada.ca: {str(e)}"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    finally:
        if driver:
            driver.quit()
            logger.info("Navegador cerrado")