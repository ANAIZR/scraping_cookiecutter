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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests
import re
from PyPDF2 import PdfReader
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = get_logger("scraper")

def scraper_agriculture_gov(url, sobrenombre):
    try:
        driver = initialize_driver()
        object_id = None

        main_folder = generate_directory(sobrenombre)
        print(f"*********** La carpeta principal es: {main_folder} ***********")

        all_urls = []
        collection, fs = connect_to_mongo("scrapping-can", "collection")
        keywords = load_keywords("plants.txt")
        scraping_failed = False

        driver.get(url)
        domain = "https://www.agriculture.gov.au"
        for keyword in keywords:
            try:
                keyword_folder = generate_directory(keyword, main_folder)
                print(f"*********** Creando carpeta para la palabra clave: {keyword_folder} ***********")

                file_path = get_next_versioned_filename(keyword_folder, keyword)
                print(f"/////////////////////////////////////////////// Se está creando el txt para {keyword}")

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#edit-search-api-fulltext--3"))
                )
                search_input.clear() 
                search_input.send_keys(keyword)

                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button#edit-submit-all-site-search--3"))
                )
                search_button.click()

                time.sleep(random.uniform(3, 6))

                content_accumulated = ""

                while True:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")

                    results_divs = soup.select("div.views-row")
                    for div in results_divs:
                        link = div.find("a", href=True)
                        if link and link["href"]:
                            href = link["href"]

                            if href.endswith((".pdf", ".docx")):
                                print(f"Ignorando archivo: {href}")
                                continue 
                            
                            if not href.startswith("http"):  
                                full_href = domain + href
                                print(f"URL encontrada: {full_href}")
                                driver.get(full_href)
                                time.sleep(random.uniform(3, 6))
                                print(f"Accediendo a la URL: {full_href}")
                                soup = BeautifulSoup(driver.page_source, "html.parser")
                                region_content_div = soup.select_one("div.region-content")
                                abstract_text = region_content_div.get_text(strip=True) if region_content_div else "No se encontró contenido en div.region-content"
                                content_accumulated += f"URL: {full_href}\nTexto: {abstract_text}\n\n"
                                content_accumulated += "-" * 100 + "\n\n"
                                driver.back()
                                WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "div.views-row")
                                )
                            )
                                time.sleep(random.uniform(3, 6))

                    try:
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "li.pager__item.pager__item--next a"))
                        )
                        next_button.click()
                        time.sleep(random.uniform(3, 6)) 
                    except (TimeoutException, NoSuchElementException):
                        break

                if content_accumulated:
                    with open(file_path, "w", encoding="utf-8") as keyword_file:
                        keyword_file.write(content_accumulated)
                    print(f"Archivo guardado correctamente")

                    with open(file_path, "rb") as file_data:
                        object_id = fs.put(
                            file_data, filename=os.path.basename(file_path),
                            metadata={
                                "keyword": keyword,
                                "scraping_date": datetime.now(),
                            },
                        )
                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                driver.get(url)

                
            except (TimeoutException, NoSuchElementException) as e:
                logger.error(f"Error al buscar '{keyword}': {e}")
                scraping_failed = True

        print(f"Total de URLs encontradas: {len(all_urls)}")

        if scraping_failed:
            return Response(
                {
                    "message": "Error durante el scraping. Algunas URLs fallaron.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            response_data= {
               "Tipo": "Web",
                "Url": url,
                "Fecha_scraper": data["Fecha_scraper"],
                "Etiquetas": data["Etiquetas"],
                "Mensaje": "Los datos han sido scrapeados correctamente.",
            }

            collection.insert_one(data)
            delete_old_documents(url, collection, fs)

            return Response(
                {
                    "data": response_data,
                },
                status=status.HTTP_200_OK,
                
            )
            """ return Response(
                {
                    "message": "Los datos han sido scrapeados correctamente.",
                    "total_keywords": len(keywords),
                    "total_urls": len(all_urls),
                },
                status=status.HTTP_200_OK,
            ) """

    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return Response(
            {"message": "La página está tardando demasiado en responder."},
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )
    except ConnectionError:
        logger.error("Error de conexión a la URL.")
        return Response(
            {"message": "No se pudo conectar a la página web."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        logger.error(f"Error al procesar datos del scraper: {str(e)}")
        return Response(
            {"message": "Ocurrió un error al procesar los datos."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()