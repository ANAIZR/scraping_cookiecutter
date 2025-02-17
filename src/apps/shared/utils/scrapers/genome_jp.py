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
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def navigate_to_next_page(driver, wait_time):
    """
    Navega a la siguiente página si es posible.
    """
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

def extract_all_data(driver, wait_time):
    """
    Extrae datos de todas las páginas y devuelve un solo bloque de texto con toda la información.
    """
    all_scraper = ""  
    record_count = 1
    skipped_rows = 0

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
                    continue

                titulo = cols[0].text.strip()
                descripcion = cols[1].text.strip()
                host_name = cols[2].text.strip()
                tipos = cols[3].text.strip()

                all_scraper += (
                    f"Registro #{record_count}:\n"
                    f"Virus(species) name: {titulo}\n"
                    f"Virus lineage: {descripcion}\n"
                    f"Host name: {host_name}\n"
                    f"Host lineage: {tipos}\n"
                    f"{'-'*80}\n"
                )

                record_count += 1

            if not navigate_to_next_page(driver, wait_time):
                break

        if skipped_rows > 0:
            all_scraper += f"\nSe omitieron {skipped_rows} filas con columnas insuficientes.\n"

        return all_scraper, record_count - 1

    except Exception as e:
        print(f"Error al extraer datos: {e}")
        return all_scraper, 0

def scraper_genome_jp(url, sobrenombre):
    """
    Scraper para Genome JP que extrae todas las páginas y almacena todo en un solo documento en MongoDB.
    """

    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    try:
        driver.get(url)
        all_scraper, total_records = extract_all_data(driver, 30)

        # 📌 **Guardar todo en un solo documento en MongoDB**
        if total_records > 0:
            object_id = fs.put(
                all_scraper.encode("utf-8"),
                source_url=url,
                scraping_date=datetime.now(),
                Etiquetas=["virus", "genome"],
                contenido=all_scraper,
                url=url
            )

            collection.insert_one(
                {
                    "_id": object_id,
                    "source_url": url,
                    "scraping_date": datetime.now(),
                    "Etiquetas": ["virus", "genome"],
                    "contenido": all_scraper,
                    "url": url,
                }
            )

            # 📌 **Eliminar versiones antiguas**
            existing_versions = list(
                collection.find({"source_url": url}).sort("scraping_date", -1)
            )

            if len(existing_versions) > 1:
                oldest_version = existing_versions[-1]
                fs.delete(ObjectId(oldest_version["_id"]))
                collection.delete_one({"_id": ObjectId(oldest_version["_id"])})

                logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")

        # 📌 **Generar el reporte en `all_scraper`**
        report = (
            f"Resumen del scraping:\n"
            f"Total de registros almacenados: {total_records}\n"
            f"Fuente: {url}\n\n"
            f"{'-'*80}\n"
        )

        response = process_scraper_data_v2(report, url, sobrenombre)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        print(f"Error general en el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
