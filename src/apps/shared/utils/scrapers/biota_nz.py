from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import pickle
import random
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
)
from rest_framework.response import Response
from rest_framework import status


def scraper_biota_nz(url, sobrenombre):
    driver = initialize_driver()
    driver.get(url)
    time.sleep(random.uniform(1, 3))

    try:
        keywords = load_keywords("plants.txt")
        if not keywords:
            raise ValueError(
                "El archivo de palabras clave está vacío o no se pudo cargar."
            )

        logger = get_logger("scraper", sobrenombre)

        base_domain = "https://biotanz.landcareresearch.co.nz"
        collection, fs = connect_to_mongo("scrapping-can", "collection")
        main_folder = generate_directory(url)
        if not main_folder:
            raise ValueError(
                f"No se pudo generar el directorio principal para la URL {url}."
            )

        visited_urls = set()
        scraping_failed = False
        logger.info("Página de BIOTA NZ cargada exitosamente.")

        for keyword in keywords:
            keyword_folder = generate_directory(keyword, main_folder)
            if not keyword_folder:
                logger.error(
                    f"No se pudo generar el directorio para la palabra clave: {keyword}"
                )
                continue

            try:
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#query"))
                )
                search_box.clear()
                search_box.send_keys(keyword)
                search_box.submit()

                while True:
                    try:
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.ID, "list-result"))
                        )
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        items = soup.select("div.row-separation.specimen-list-item")

                        for item in items:
                            try:
                                href_element = item.select_one("div.col-12 > a[href]")
                                if not href_element:
                                    continue

                                href = href_element["href"]
                                full_url = f"{base_domain}{href}"

                                link_folder = generate_directory(href, keyword_folder)
                                if not link_folder:
                                    logger.error(
                                        f"No se pudo generar el directorio para el enlace: {href}"
                                    )
                                    continue

                                file_path = get_next_versioned_filename(
                                    link_folder, keyword
                                )
                                if not file_path:
                                    logger.error(
                                        f"No se pudo generar el archivo para {href}"
                                    )
                                    continue

                                driver.get(full_url)
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "div.page-content-wrapper")
                                    )
                                )
                                soup = BeautifulSoup(driver.page_source, "html.parser")
                                body = soup.select_one("div.page-content-wrapper")
                                body_text = (
                                    body.get_text(strip=True)
                                    if body
                                    else "No body found"
                                )

                                with open(file_path, "w", encoding="utf-8") as file:
                                    file.write(body_text)

                                with open(file_path, "rb") as file_data:
                                    object_id = fs.put(
                                        file_data, filename=os.path.basename(file_path)
                                    )

                                driver.back()
                            except Exception as e:
                                logger.error(f"Error procesando item: {str(e)}")
                                continue

                        next_page = driver.find_element(
                            By.XPATH,
                            "//a[contains(@class, 'paging-hyperlink') and contains(text(), 'Next')]",
                        )
                        driver.execute_script("arguments[0].click();", next_page)
                        time.sleep(random.uniform(3, 6))
                    except Exception as e:
                        logger.info("No hay más páginas disponibles.")
                        break

            except Exception as e:
                logger.error(
                    f"Error al procesar la palabra clave '{keyword}': {str(e)}"
                )
                scraping_failed = True

        if scraping_failed:
            return Response(
                {"message": "Error durante el scraping. Algunas URLs fallaron."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = {
            "Objecto": object_id,
            "Tipo": "Web",
            "Url": url,
            "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["planta", "plaga"],
        }
        collection.insert_one(data)
        delete_old_documents(url, collection, fs)
        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error general: {str(e)}")
        return {"status": "error", "message": f"Error general: {str(e)}"}
    finally:
        driver.quit()
