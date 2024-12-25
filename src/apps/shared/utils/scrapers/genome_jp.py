from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
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

def extract_data(driver, wait_time):

    all_scraper = ""
    record_count = 1
    skipped_rows = 0

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

            all_scraper += f"Registro #{record_count} : \n"
            all_scraper += f"Virus(species) name :      {titulo}\n"
            all_scraper += f"Virus lineage       :      {descripcion}\n"
            all_scraper += f"Host name           :      {host_name}\n"
            all_scraper += f"Host lineage        :      {tipos}\n"
            all_scraper += "-------------------------------------------\n\n"

            record_count += 1

        if skipped_rows > 0:
            print(f"Se omitieron {skipped_rows} filas con columnas insuficientes.")

        return all_scraper
    except Exception as e:
        print(f"Error al extraer datos: {e}")
        return all_scraper

def scraper_genome_jp(url, wait_time, sobrenombre):

    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    try:
        driver.get(url)

        while True:
            data = extract_data(driver, wait_time)
            all_scraper += data

            if not navigate_to_next_page(driver, wait_time):
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        print(f"Error general en el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
