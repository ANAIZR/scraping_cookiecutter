from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
from datetime import datetime
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def navigate_to_next_page(driver, wait_time):
    try:
        next_button = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.next"))
        )
        next_button.click()
        time.sleep(2)
        return True
    except Exception as e:
        print(f"No se pudo navegar a la siguiente página: {e}")
        return False

def extract_data(driver, wait_time, fs, logger, url):
    all_scraper = ""
    record_count = 1
    skipped_rows = 0
    total_scraped_successfully = 0
    
    try:
        tbody = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, "//table/tbody[2]"))
        )
        rows = tbody.find_elements(By.CSS_SELECTOR, "tr")

        for row in rows:
            cols = row.find_elements(By.CSS_SELECTOR, "td")

            if len(cols) < 4:
                skipped_rows += 1
                continue

            titulo = cols[0].text.strip()
            descripcion = cols[1].text.strip()
            host_name = cols[2].text.strip()
            tipos = cols[3].text.strip()
            
            # Extraer enlaces dentro de la fila
            link_elements = row.find_elements(By.TAG_NAME, "a")
            for link in link_elements:
                link_href = link.get_attribute("href")
                if link_href:
                    driver.get(link_href)
                    time.sleep(2)
                    content_text = driver.find_element(By.TAG_NAME, "body").text
                    
                    if content_text:
                        object_id = fs.put(
                            content_text.encode("utf-8"),
                            source_url=link_href,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=content_text,
                            url=url
                        )
                        total_scraped_successfully += 1
                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                        
                        existing_versions = list(fs.find({"source_url": link_href}).sort("scraping_date", -1))
                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(ObjectId(oldest_version["_id"]))
                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")

            all_scraper += f"Registro #{record_count} : \n"
            all_scraper += f"Virus(species) name :      {titulo}\n"
            all_scraper += f"Virus lineage       :      {descripcion}\n"
            all_scraper += f"Host name           :      {host_name}\n"
            all_scraper += f"Host lineage        :      {tipos}\n"
            all_scraper += "-------------------------------------------\n\n"

            record_count += 1

        if skipped_rows > 0:
            print(f"Se omitieron {skipped_rows} filas con columnas insuficientes.")

        return all_scraper, total_scraped_successfully
    except Exception as e:
        print(f"Error al extraer datos: {e}")
        return all_scraper, total_scraped_successfully

def scraper_genome_jp(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    try:
        driver.get(url)

        while True:
            data, total_scraped_successfully = extract_data(driver, 30, fs, logger, url)
            all_scraper += data

            if not navigate_to_next_page(driver, 30):
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info(f"Total de enlaces visitados y almacenados: {total_scraped_successfully}")
        return response

    except Exception as e:
        print(f"Error general en el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado")
