from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def navigate_multiple_pages(driver, wait_time, max_pages=3):
    """Navega a la siguiente página hasta un máximo de `max_pages` veces."""
    pages_navigated = 0  # Contador de páginas visitadas

    while pages_navigated < max_pages:
        try:
            next_button = WebDriverWait(driver, wait_time).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.next"))
            )
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(2)  # Esperar a que cargue la siguiente página
            pages_navigated += 1
            print(f"Página {pages_navigated}: Se hizo clic en 'Next'.")
        except Exception as e:
            print(f"Intento fallido en la página {pages_navigated + 1}: {e}")
            break  # Salir del bucle si no puede hacer clic en 'Next'

    print(f"Navegación finalizada. Se avanzó hasta {pages_navigated} páginas.")

def extract_all_data(driver, wait_time):
    """Extrae los datos y genera un reporte con la cantidad de URLs procesadas."""

    all_scraper = ""  
    record_count = 0
    skipped_rows = 0
    total_urls_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    urls_scraped = []
    urls_not_scraped = []

    try:
        while True:
            tbody = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, "//table/tbody[2]"))
            )
            rows = tbody.find_elements(By.CSS_SELECTOR, "tr")

            for row in rows:
                cols = row.find_elements(By.CSS_SELECTOR, "td")

                if len(cols) < 4:
                    skipped_rows += 1
                    total_failed_scrapes += 1
                    urls_not_scraped.append(row.text)
                    continue

                titulo = cols[0].text.strip()
                descripcion = cols[1].text.strip()
                host_name = cols[2].text.strip()
                tipos = cols[3].text.strip()

                if titulo and descripcion and host_name and tipos:
                    total_scraped_successfully += 1
                    urls_scraped.append(f"{titulo} ({host_name})")

                all_scraper += (
                    f"Registro #{record_count + 1}:\n"
                    f"Virus(species) name: {titulo}\n"
                    f"Virus lineage: {descripcion}\n"
                    f"Host name: {host_name}\n"
                    f"Host lineage: {tipos}\n"
                    f"{'-'*80}\n"
                )

                record_count += 1

            total_urls_found += len(rows)

            if not navigate_multiple_pages(driver, wait_time):
                break

        if skipped_rows > 0:
            all_scraper += f"\nSe omitieron {skipped_rows} filas con columnas insuficientes.\n"

        return all_scraper, record_count, total_urls_found, total_scraped_successfully, total_failed_scrapes, urls_scraped, urls_not_scraped

    except Exception as e:
        print(f"Error al extraer datos: {e}")
        return all_scraper, 0, 0, 0, 0, [], []

def scraper_genome_jp(url, sobrenombre):
    """Ejecuta el scraper y almacena los datos en MongoDB."""

    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    try:
        (
            all_scraper, total_records, total_urls_found, 
            total_scraped_successfully, total_failed_scrapes, 
            urls_scraped, urls_not_scraped
        ) = extract_all_data(driver, 30)

        if total_records > 0:
            object_id = fs.put(
                all_scraper.encode("utf-8"),
                source_url=url,
                scraping_date=datetime.now(),
                Etiquetas=["virus", "genome"],
                contenido=all_scraper,
                url=url
            )

            existing_versions = list(
                fs.find({"source_url": url}).sort("scraping_date", -1)
            )

            if len(existing_versions) > 1:
                oldest_version = existing_versions[-1]
                fs.delete(oldest_version._id)  
                logger.info(f"Se eliminó la versión más antigua en GridFS con object_id: {oldest_version._id}")

        report = (
            f"Resumen del scraping:\n"
            f"Fuente: {url}\n"
            f"Total de URLs encontradas: {total_urls_found}\n"
            f"Total de URLs scrapeadas exitosamente: {total_scraped_successfully}\n"
            f"Total de URLs fallidas/no procesadas: {total_failed_scrapes}\n"
            f"Total de registros almacenados: {total_records}\n\n"
            f"{'-'*80}\n"
            f"Enlaces scrapeados:\n" + "\n".join(urls_scraped) + "\n\n"
            f"Enlaces no procesados:\n" + "\n".join(urls_not_scraped) + "\n"
        )

        response = process_scraper_data(report, url, sobrenombre)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        print(f"Error general en el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
