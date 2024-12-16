from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time

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

def scrape_genome_jp(url, wait_time, sobrenombre):

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--ignore-certificate-errors") 
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    try:
        driver.get(url)
        all_scraper = ""

        while True:
            data = extract_data(driver, wait_time)
            all_scraper += data

            if not navigate_to_next_page(driver, wait_time):
                break

        if all_scraper.strip():
            response_data = save_scraped_data(
                all_scraper, url, sobrenombre, collection, fs
            )
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos para scrapear.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )

    except Exception as e:
        print(f"Error general en el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
