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
    get_next_versioned_pdf_filename,
    process_scraper_data,
    load_keywords
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import json
import time
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests
import re
from bs4 import BeautifulSoup
from pypdf import PdfReader, PdfWriter
from io import BytesIO
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from pathlib import Path

logger = get_logger("scraper")

def scraper_cdfa(url, sobrenombre):
    driver = initialize_driver()
    all_hrefs = []
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    keywords = load_keywords("plants.txt")
    all_scraper = ""
    total_urls_found = 0
    total_urls_scraped = 0
    urls_not_scraped = []
    visited_urls = set()
    urls_to_scrape = []

    def scrape_page(href, keyword_dir):
        nonlocal total_urls_found, total_urls_scraped, all_scraper
        try:
            print(f"Procesando URL: {href}")
            response = requests.get(href)
            if response.status_code != 200:
                logger.error(f"Error HTTP al acceder a {href}: {response.status_code}")
                return []

            content_type = response.headers.get("Content-Type", "")
            sanitized_href = href.replace(":", "_").replace("/", "_")
            keyword_folder = os.path.join(keyword_dir, sanitized_href[:50]) 
            if not os.path.exists(keyword_folder):
                os.makedirs(keyword_folder)
            print(f"Generando directorio para el enlace: {keyword_folder}")

            file_name = href.split("/")[-1].split(".")[0]
            if len(file_name) > 50:
                file_name = hashlib.md5(file_name.encode()).hexdigest()[:10]

            if href.endswith(".html"):
                print(f"Procesando página HTML: {href}")
                soup = BeautifulSoup(response.text, "html.parser")

                table = soup.select_one("table.mytable tbody")
                if table:
                    table_hrefs = [
                        link.get("href") for link in table.find_all("a", href=True)
                    ]
                    if table_hrefs:
                        print(f"Enlaces encontrados en la tabla: {table_hrefs}")
                        for table_href in table_hrefs:
                            full_url = requests.compat.urljoin(href, table_href)
                            all_hrefs.append((full_url, keyword_folder)) 
                            total_urls_found += 1

                            if full_url.endswith(".pdf"):
                                print(f"Procesando PDF encontrado en tabla: {full_url}")
                                pdf_response = requests.get(full_url)
                                if pdf_response.status_code == 200:
                                    pdf_file_path = get_next_versioned_pdf_filename(keyword_folder, base_name=file_name)
                                    with open(pdf_file_path, "wb") as file:
                                        file.write(pdf_response.content)
                                    print(f"PDF guardado desde tabla en: {pdf_file_path}")
                else:
                    body_text = soup.body.get_text(strip=True) if soup.body else ""
                    file_path = get_next_versioned_filename(keyword_folder, base_name=file_name)
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(f"URL: {href}\n\n{body_text}")
                    print(f"Contenido de página guardado en: {file_path}")

            elif "application/pdf" in content_type or href.endswith(".pdf"):
                print(f"Procesando PDF: {href}")
                file_path = get_next_versioned_pdf_filename(keyword_folder, base_name=file_name)
                with open(file_path, "wb") as file:
                    file.write(response.content)
                try:
                    PdfReader(BytesIO(response.content))
                    print(f"PDF guardado en: {file_path}")
                except Exception as e:
                    os.remove(file_path)
                    logger.error(f"El contenido descargado no es un PDF válido: {e}")
            else:
                print(f"Contenido desconocido o no soportado: {href}")
            total_urls_scraped += 1
            return []
        except Exception as e:
            logger.error(f"Error al procesar URL {href}: {str(e)}")
            urls_not_scraped.append(href)
            return []

    def scrape_pages_in_parallel(url_list):
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {
                executor.submit(scrape_page, href, keyword_dir): (href, keyword_dir)
                for href, keyword_dir in url_list
            }
            for future in as_completed(future_to_url):
                try:
                    new_links = future.result()
                    if new_links:
                        all_hrefs.extend(new_links)
                except Exception as e:
                    logger.info(f"Error en tarea de scraping: {str(e)}")

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 30)
        time.sleep(random.uniform(3, 6))
        print("Iniciando scrapeo")
        main_folder = generate_directory(url)

        for keyword in keywords:
            try:
                keyword_dir = os.path.join(main_folder, keyword.replace(" ", "_"))
                if not os.path.exists(keyword_dir):
                    os.makedirs(keyword_dir)
                print(f"Carpeta creada para palabra clave: {keyword_dir}")

                driver.get(url)
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div#head-search input"))
                )
                if search_box:
                    print("Se encontró search")
                    search_box.clear()
                    search_box.send_keys(keyword)
                    time.sleep(random.uniform(1, 3))
                    search_box.submit()
                    time.sleep(random.uniform(1, 3))
                    print("Ingresaremos a buscar")

            except:
                print("No se encontró search")
                continue
            
            while True:
                try:
                    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.gs-title a")))
                    links = driver.find_elements(By.CSS_SELECTOR, "div.gs-title a")
                    print("Buscando href de la palabra")
                    hrefs = [
                        link.get_attribute("href")
                        for link in links
                        if link.get_attribute("href") and "staff" not in link.get_attribute("href").lower()
                    ]
                    if not hrefs:
                        print("No se encontraron hrefs")
                        break
                    for href in hrefs:
                        all_hrefs.append((href, keyword_dir)) 
                        total_urls_found += 1
                        print(f"Enlace encontrado: {href}")

                    paginator = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.gsc-cursor"))
                    )
                    if paginator:
                        print("Se encontró paginator")

                        pages = paginator.find_elements(By.CSS_SELECTOR, "div.gsc-cursor-page")
                        
                        for i in range(len(pages)):
                            try:
                                paginator = driver.find_element(By.CSS_SELECTOR, "div.gsc-cursor")
                                pages = paginator.find_elements(By.CSS_SELECTOR, "div.gsc-cursor-page")
                                
                                driver.execute_script("arguments[0].scrollIntoView();", pages[i])
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", pages[i])
                                time.sleep(random.uniform(2, 4)) 

                                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.gs-title a")))
                                new_links = driver.find_elements(By.CSS_SELECTOR, "div.gs-title a")
                                print("Buscando href de la nueva página")
                                new_hrefs = [
                                    link.get_attribute("href")
                                    for link in new_links
                                    if link.get_attribute("href") and "staff" not in link.get_attribute("href").lower()
                                ]
                                for href in new_hrefs:
                                    all_hrefs.append((href, keyword_dir))
                                    total_urls_found += 1
                                    print(f"Enlace encontrado: {href}")
                            except Exception as e:
                                print(f"Error al procesar la página: {pages[i].text}. Detalle: {e}")
                                break
                        break
                    else:
                        print("No se encontró paginador")
                        break
                except TimeoutException:
                    print(f"No se encontraron enlaces para la palabra clave {keyword}.")
                    break
    finally:
        driver.quit()

    unique_hrefs = list(set(all_hrefs)) 

    scrape_pages_in_parallel(unique_hrefs)

    all_scraper = (
        f"Resumen del scraping:\n"
        f"Total de URLs encontradas: {total_urls_found}\n"
        f"Total de URLs scrapeadas: {total_urls_scraped}\n"
        f"Total de URLs no scrapeadas: {len(urls_not_scraped)}\n\n"
        f"{'-'*80}\n\n"
    ) + all_scraper

    if urls_not_scraped:
        all_scraper += "URLs no scrapeadas:\n\n"
        all_scraper += "\n".join(urls_not_scraped) + "\n"

    response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
    return response