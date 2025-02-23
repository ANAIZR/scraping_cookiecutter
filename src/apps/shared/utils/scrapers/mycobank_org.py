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

def close_modal(driver):
    """Cierra el modal emergente de cada fila."""
    try:
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.header-action.action-close"))
        )
        driver.execute_script("arguments[0].click();", close_button)
    except Exception:
        pass  

def scraper_mycobank_org(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    content_text = ""  # Para almacenar toda la data en MongoDB
    all_scraper = ""  # Para generar un reporte del scraping
    total_rows_found = 0  # Total de filas encontradas
    total_scraped_successfully = 0  # Total de filas scrapeadas
    total_failed_scrapes = 0  # Total de filas no scrapeadas

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#search-btn"))
        )
        driver.execute_script("document.querySelector('#search-btn').click();")
        time.sleep(5)

        while True:
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.mat-table tbody tr"))
            )
            time.sleep(5)
            rows = driver.find_elements(By.CSS_SELECTOR, "table.mat-table tbody tr")
            total_rows_found += len(rows)  # Contamos cuántas filas hay en la tabla

            for index, row in enumerate(rows, start=1):
                try:
                    link = row.find_element(By.CSS_SELECTOR, "td a")
                    link_href = link.get_attribute("href")
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(5)

                    popup_title = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.mat-dialog-title"))
                    ).text

                    popup_content = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.first-column"))
                    ).text

                    # Concatenamos toda la información en `content_text`
                    content_text += f"Registro {index}\n"
                    content_text += f"Title: {popup_title}\n"
                    content_text += f"URL: {link_href}\n"
                    content_text += f"Content:\n{popup_content}\n"
                    content_text += "-" * 80 + "\n\n"

                    total_scraped_successfully += 1

                    close_modal(driver)

                except Exception as e:
                    logger.error(f"Error en la fila {index}: {e}")
                    total_failed_scrapes += 1  # Contamos los fallos
                    continue

            # Intentar avanzar a la siguiente página
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next page']")
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(5)
            except Exception:
                logger.info("No hay más páginas para procesar.")
                break  

        # Generar reporte de scraping
        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de filas encontradas: {total_rows_found}\n"
            f"Total de filas scrapeadas: {total_scraped_successfully}\n"
            f"Total de filas no scrapeadas: {total_failed_scrapes}\n\n"
            f"{'-'*80}\n\n"
        )

        if total_failed_scrapes > 0:
            all_scraper += "Enlaces no scrapeados:\n"
            all_scraper += f"Total: {total_failed_scrapes}\n\n"

        if content_text.strip():
            object_id = fs.put(
                content_text.encode("utf-8"),
                source_url=url,
                scraping_date=datetime.now(),
                Etiquetas=["planta", "micología"],
                contenido=content_text,
                url=url
            )

            logger.info(f"Documento completo almacenado en MongoDB con object_id: {object_id}")

            existing_versions = list(fs.find({"source_url": url}).sort("scraping_date", -1))
            if len(existing_versions) > 1:
                oldest_version = existing_versions[-1]
                fs.delete(ObjectId(oldest_version["_id"]))
                logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response(
            {"error": f"Ocurrió un error durante el scraping: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
        logger.info("Navegador cerrado")
