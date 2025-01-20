from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
)

logger = get_logger("scraper")


def process_results(driver, base_domain, keyword_folder, fs):
    """Procesa los resultados de una página."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.select("div.row-separation.specimen-list-item")
    if not items:
        logger.warning("No se encontraron resultados en esta página.")
        return False

    logger.info(f"Encontrados {len(items)} resultados.")
    for item in items:
        try:
            href_element = item.select_one("div.col-12 > a[href]")
            if not href_element:
                continue
            href = href_element["href"]
            logger.info(f"Procesando enlace: {href}")
            full_url = f"{base_domain}{href}"

            driver.get(full_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.page-content-wrapper"))
            )
            time.sleep(random.uniform(6, 10))

            soup = BeautifulSoup(driver.page_source, "html.parser")
            body = soup.select_one("div.page-content-wrapper")
            body_text = body.get_text(strip=True) if body else "No body found"
            if body_text:
                file_path = save_content(body_text, href, keyword_folder)
                save_to_mongo(fs, file_path)
            else:
                logger.warning(f"No se encontró contenido en la página: {full_url}")
        except Exception as e:
            logger.error(f"Error procesando elemento: {e}")
            continue
    return True


def save_content(content, href, keyword_folder):
    """Guarda el contenido de la página en un archivo."""
    link_folder = generate_directory(href, keyword_folder)
    file_path = get_next_versioned_filename(link_folder, href)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)
    logger.info(f"Contenido guardado en: {file_path}")
    return file_path


def save_to_mongo(fs, file_path):
    """Guarda el archivo en MongoDB."""
    with open(file_path, "rb") as file_data:
        object_id = fs.put(file_data, filename=os.path.basename(file_path))
    logger.info(f"Archivo guardado en MongoDB con ID: {object_id}")
    return object_id


def navigate_to_next_page(driver):
    """Navega a la siguiente página si existe."""
    try:
        next_page = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@class, 'paging-hyperlink') and contains(text(), 'Next')]")
            )
        )
        driver.execute_script("arguments[0].click();", next_page)
        time.sleep(random.uniform(6, 10))
        return True
    except Exception:
        logger.info("No hay más páginas disponibles o el botón no es clickeable.")
        return False


def scraper_biota_nz(url, sobrenombre):
    driver = initialize_driver()
    base_domain = "https://biotanz.landcareresearch.co.nz"

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")

        collection, fs = connect_to_mongo("scrapping-can", "collection")
        main_folder = generate_directory(url)
        keywords = load_keywords("plants.txt")
        if not keywords:
            return Response(
                {"message": "El archivo de palabras clave está vacío o no se pudo cargar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scraping_failed = False

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")
            keyword_folder = generate_directory(keyword, main_folder)

            try:
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#query"))
                )
                search_box.clear()
                search_box.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                search_box.submit()
            except Exception as e:
                logger.error(f"Error al buscar la palabra clave '{keyword}': {e}")
                scraping_failed = True
                continue

            while True:
                if not process_results(driver, base_domain, keyword_folder, fs):
                    break
                if not navigate_to_next_page(driver):
                    break

        if scraping_failed:
            return Response(
                {"message": "Error durante el scraping. Algunas palabras clave fallaron."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"status": "success", "message": "Scraping completado con éxito."},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response(
            {"status": "error", "message": f"Error durante el scraping: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        driver.quit()
