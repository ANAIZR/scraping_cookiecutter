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

def scraper_apsnet(url, sobrenombre):
    driver = None
    try:
        driver = initialize_driver()
        object_id = None

        main_folder = generate_directory(sobrenombre)
        print(f"*********** La carpeta principal es: {main_folder} ***********")

        all_urls = []
        collection, fs = connect_to_mongo("scrapping-can", "collection")
        keywords = load_keywords("plants.txt")
        scraping_failed = False
        visited_urls = set()
        urls_not_scraped = []
        total_urls_found = 0
        total_urls_scraped = 0

        driver.get(url)
        domain = "https://apsjournals.apsnet.org"
        for keyword in keywords:
            try:
                driver.get(url)
                time.sleep(2)

                keyword_folder = generate_directory(keyword, main_folder)
                print(f"*********** La carpeta para {keyword} es: {keyword_folder} ********")

                file_path = get_next_versioned_filename(keyword_folder, keyword)
                print(f"/////////////////////////////////////////////// Se está creando el txt para {keyword}")

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#text1"))
                )

                search_input.clear()
                search_input.send_keys(keyword)

                search_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button#advanced-search-btn"))
                )
                search_button.click()
                time.sleep(random.uniform(3,6))

                content_accumulated = ""

                hrefs = []
                while True:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    results_divs = soup.select("ul.rlist.search-result__body li.search__item")
                    for div in results_divs:
                        link = div.find("a", href=True)
                        if link and link["href"]:
                            full_href = domain + link["href"] if not link["href"].startswith("http") else link["href"]
                            hrefs.append(full_href)
                            total_urls_found += 1
                    try:
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.pagination__btn--next"))
                        )

                        next_page_url = next_button.get_attribute("href")
                        if "startPage=" in next_page_url:
                            next_page_number = int(next_page_url.split("startPage=")[1].split("&")[0])
                        else:
                            next_page_number = current_page + 1

                        if next_page_number > 9:
                            logger.info(f"Se ha alcanzado la página límite (10). Deteniendo la paginación.")
                            break
                        next_button.click()
                        time.sleep(random.uniform(3,6))
                    except (TimeoutException, NoSuchElementException):
                        break
                
                for idx, link in enumerate(hrefs, start=1):
                    try:
                        print(f"Se está scrapeando ({idx}) y el link es: {link}")
                        driver.get(link)
                        time.sleep(random.uniform(3,6))
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        content_div = soup.select_one("div.article__body")
                        
                        if not content_div:
                            logger.warning(f"No se encontró 'div.article__body' en {link}. Intentando con 'div.abstract'")
                            content_div = soup.select_one("div.abstract")

                        if not content_div:
                            logger.warning(f"No se encontró contenido relevante en {link}. Guardando HTML completo.")
                            content_accumulated += f"URL: {link}\nTexto: {soup.get_text(strip=True)}\n{'-' * 100}\n\n"
                        else:
                            abstract_text = content_div.get_text(strip=True)
                            content_accumulated += f"URL: {link}\nTexto: {abstract_text}\n{'-' * 100}\n\n"
                        visited_urls.add(link)
                        total_urls_scraped += 1
                        driver.back()
                        time.sleep(random.uniform(3,6))
                    except Exception as e:
                        urls_not_scraped.append(link)
                        logger.error(f"Error al procesar la URL: {link}. Error: {str(e)}")
                        scraping_failed = True
                        break

                if content_accumulated:
                    with open(file_path, "w", encoding="utf-8") as keyword_file:
                        keyword_file.write(content_accumulated)
                    print(f"Archivo guardado correctamente: {file_path}")

                    with open(file_path, "rb") as file_data:
                        object_id = fs.put(
                            file_data,
                            filename=os.path.basename(file_path),
                            metadata={
                                "keyword": keyword,
                                "scraping_date": make_aware(datetime.now()),
                            },
                        )
                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

            except (TimeoutException, NoSuchElementException, WebDriverException) as e:
                logger.error(f"Error al buscar '{keyword}': {e}")
                scraping_failed = True

        driver.quit()

        if scraping_failed:
            return Response(
                {"message": "Error durante el scraping. Algunas URLs fallaron."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scraper": make_aware(datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            response_data = {
                "Tipo": "Web",
                "Url": url,
                "Fecha_scraper": data["Fecha_scraper"],
                "Etiquetas": data["Etiquetas"],
                "Mensaje": "Los datos han sido scrapeados correctamente.",
            }
            collection.insert_one(data)
            delete_old_documents(url, collection, fs)

            return Response(
                {"data": response_data},
                status=status.HTTP_200_OK,
            )
    except Exception as e:
        logger.error(f"Error durante el scrapeo: {str(e)}")
        return Response(
            {"error": f"Error durante el scrapeo: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        if driver:
            driver.quit()