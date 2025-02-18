import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import logging
from rest_framework.response import Response
from rest_framework import status
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from ..functions import (
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    load_keywords
)

logger = get_logger("scraper")

def scraper_cdfa(url, sobrenombre):
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    keywords = load_keywords("plants.txt")

    if not keywords:
        return Response(
            {"status": "error", "message": "El archivo de palabras clave está vacío o no se pudo cargar."},
            status=status.HTTP_400_BAD_REQUEST
        )

    main_folder = generate_directory(sobrenombre)
    all_urls = set()  # Conjunto para evitar duplicados
    visited_urls = set()

    total_urls_found = 0

    try:
        driver.get(url)
        time.sleep(random.uniform(3, 6))

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")
            keyword_dir = os.path.join(main_folder, keyword.replace(" ", "_"))
            os.makedirs(keyword_dir, exist_ok=True)

            try:
                driver.get(url)
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div#head-search input"))
                )
                search_box.clear()
                search_box.send_keys(keyword)
                time.sleep(random.uniform(1, 3))
                search_box.submit()
                time.sleep(random.uniform(1, 3))
            except Exception as e:
                logger.error(f"Error al buscar la palabra clave '{keyword}': {e}")
                continue

            while True:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.gsc-expansionArea div.gsc-webResult.gsc-result"))
                    )
                    results = driver.find_elements(By.CSS_SELECTOR, "div.gsc-expansionArea div.gsc-webResult.gsc-result")

                    if not results:
                        break

                    for result in results:
                        try:
                            link_element = result.find_element(By.CSS_SELECTOR, "div.gs-title a")
                            href = link_element.get_attribute("href") if link_element else None

                            if href and "staff" not in href.lower() and href not in visited_urls:
                                all_urls.add(href)
                                total_urls_found += 1
                                print(f"Enlace encontrado: {href}")

                        except Exception:
                            continue

                    # Manejo de paginación con verificación de existencia
                    try:
                        paginator = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.gsc-cursor"))
                        )
                        pages = paginator.find_elements(By.CSS_SELECTOR, "div.gsc-cursor-page")

                        for i in range(len(pages)):
                            try:
                                paginator = WebDriverWait(driver, 5).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.gsc-cursor"))
                                )
                                pages = paginator.find_elements(By.CSS_SELECTOR, "div.gsc-cursor-page")
                                if i >= len(pages):  
                                    break

                                page = pages[i]
                                driver.execute_script("arguments[0].scrollIntoView();", page)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", page)
                                time.sleep(random.uniform(2, 4))

                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.gs-title a"))
                                )
                                new_links = driver.find_elements(By.CSS_SELECTOR, "div.gs-title a")

                                for link in new_links:
                                    new_href = link.get_attribute("href")
                                    if new_href and "staff" not in new_href.lower() and new_href not in visited_urls:
                                        all_urls.add(new_href)
                                        total_urls_found += 1
                                        print(f"Enlace encontrado en paginación: {new_href}")

                            except Exception:
                                continue

                        break
                    except TimeoutException:
                        print("No se encontró la paginación.")
                        break
                except TimeoutException:
                    print("No se encontraron más resultados en esta página.")
                    break

        # PROCESAR TODAS LAS URLs RECOGIDAS
        print(f"Total de enlaces encontrados: {len(all_urls)}")
        new_urls = list(all_urls)  # Convertimos a lista para iterar

        for href in new_urls:
            if href in visited_urls:
                continue

            visited_urls.add(href)
            print(f"Procesando página: {href}")

            try:
                response = requests.get(href, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    table = soup.select_one("table.mytable tbody")

                    if table:
                        table_hrefs = [link.get("href") for link in table.find_all("a", href=True)]
                        for table_href in table_hrefs:
                            full_url = requests.compat.urljoin(href, table_href)
                            if full_url not in visited_urls:
                                all_urls.add(full_url)
                                total_urls_found += 1
                                print(f"Nuevo enlace encontrado en tabla: {full_url}")

                    else:
                        body_text = soup.body.get_text(strip=True) if soup.body else ""
                        file_path = os.path.join(main_folder, f"document_{len(visited_urls)}.txt")
                        with open(file_path, "w", encoding="utf-8") as file:
                            file.write(f"URL: {href}\n\n{body_text}")
                        print(f"Contenido guardado en: {file_path}")

            except Exception as e:
                print(f"Error al procesar {href}: {e}")

    finally:
        driver.quit()

    return Response(
        {
            "status": "success",
            "message": "Scraping finalizado",
            "total_urls_found": total_urls_found,
            "total_urls_scraped": len(visited_urls),
            "all_urls": list(all_urls)
        },
        status=status.HTTP_200_OK
    )
