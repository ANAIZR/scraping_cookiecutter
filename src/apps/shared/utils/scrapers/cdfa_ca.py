from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
import os
import logging
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    load_keywords
)
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException


logger = get_logger("scraper")

def scraper_cdfa(url, sobrenombre):
    driver = initialize_driver()
    all_hrefs = []
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    keywords = load_keywords("plants.txt")
    total_urls_found = 0
    total_urls_scraped = 0
    urls_not_scraped = []

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 30)
        time.sleep(random.uniform(3, 6))
        logger.info(f"Iniciando scraping para URL: {url}")
        main_folder = generate_directory(sobrenombre)

        if not keywords:
            return Response(
                {
                    "status": "error",
                    "message": "El archivo de palabras clave está vacío o no se pudo cargar."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.gs-title a")))
                    links = driver.find_elements(By.CSS_SELECTOR, "div.gs-title a")
                    print("/////Buscando href de la palabra")
                    hrefs = [
                        link.get_attribute("href")
                        for link in links
                        if link.get_attribute("href") and "staff" not in link.get_attribute("href").lower()
                    ]
                    if not hrefs:
                        print("///No se encontraron hrefs")
                        break
                    for href in hrefs:
                        all_hrefs.append((href, keyword_dir)) 
                        total_urls_found += 1
                        print(f"////Enlace encontrado: {href}")

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

    return Response(
        {
            "status": "success",
            "message": "Scraping finalizado",
            "total_urls_found": total_urls_found,
            "total_urls_scraped": total_urls_scraped,
            "total_urls_not_scraped": len(urls_not_scraped),
            "urls_not_scraped": urls_not_scraped
        },
        status=status.HTTP_200_OK,
    )
