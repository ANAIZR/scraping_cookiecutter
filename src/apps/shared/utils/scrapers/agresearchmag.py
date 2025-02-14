from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
    get_logger,
    connect_to_mongo,
)
from rest_framework.response import Response
from rest_framework import status
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException

logger = get_logger("scraper")

def scraper_agresearchmag(url, sobrenombre):
    driver = initialize_driver()
    domain = "https://agresearchmag.ars.usda.gov"
    fullhrefs = []

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")

        collection, fs = connect_to_mongo()
        main_folder = generate_directory(sobrenombre)

        panel = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.panel-body ul.als-wrapper"))
        )

        next_button_selector = "span.als-next"
        max_attempts = 10
        attempts = 0
        last_index = 0

        while attempts < max_attempts:
            li_elements = panel.find_elements(By.CSS_SELECTOR, "li.als-item")

            if not li_elements:
                logger.warning("No se encontraron elementos <li>. Saliendo del bucle.")
                break

            for index in range(last_index, len(li_elements)):
                try:
                    li = li_elements[index]
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(li)).click()
                    time.sleep(random.uniform(3, 5))

                    active_class = li.get_attribute("class")
                    if "active" in active_class:
                        logger.info(f"Elemento {index+1} activado correctamente.")

                        text_center_divs = driver.find_elements(By.CSS_SELECTOR, "div.text-center a")
                        for link in text_center_divs:
                            href = link.get_attribute("href")
                            if href:
                                fullhref = domain + href if not href.startswith("http") else href
                                fullhrefs.append(fullhref)
                                logger.info(f"Enlace extraído: {fullhref}")
                    else:
                        logger.warning(f"Elemento {index+1} no se activó correctamente.")
                except (ElementClickInterceptedException, TimeoutException) as e:
                    logger.error(f"No se pudo hacer clic en el elemento {index+1}: {str(e)}")
                    last_index = index
                    break
            
            try:
                next_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, next_button_selector)))
                next_button.click()
                logger.info("Clic en 'siguiente' realizado. Cargando más elementos...")
                time.sleep(random.uniform(4, 6))
                attempts += 1
                last_index += 1
            except (TimeoutException, NoSuchElementException):
                logger.info("No se encontró el botón 'siguiente' o ya no hay más elementos. Terminando.")
                break
    
    except TimeoutException:
        return Response(
            {"status": "error", "message": "Error al cargar la página."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return Response(
            {"status": "error", "message": f"Error inesperado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
        logger.info("Scraping finalizado en la primera fase.")

    extracted_data = {}

    for href in fullhrefs:
        try:
            driver = initialize_driver()
            driver.get(href)
            time.sleep(random.uniform(3, 6))

            try:
                third_row = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.row:nth-of-type(3)"))
                )
                extracted_html = third_row.get_attribute("outerHTML")
                logger.info(f"Extraído div.row:nth-of-type(3) de {href}")
            except TimeoutException:
                body = driver.find_element(By.TAG_NAME, "body")
                extracted_html = body.get_attribute("outerHTML")
                logger.info(f"No se encontró div.row:nth-of-type(3), extrayendo body de {href}")

            # Extraer solo el texto limpio
            soup = BeautifulSoup(extracted_html, "html.parser")
            body_text = soup.get_text(separator="\n", strip=True)

            extracted_data[href] = body_text

            # Guardar en un archivo versionado con el formato requerido
            file_path = get_next_versioned_filename(main_folder, sobrenombre)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(f"URL: {href}\nTexto: {body_text}\n\n" + "-" * 100 + "\n\n")

        except Exception as e:
            logger.error(f"Error al extraer datos de {href}: {str(e)}")
        
        finally:
            driver.quit()

    logger.info("Extracción de contenido finalizada.")

    return Response(
        {
            "status": "success",
            "message": "Scraping finalizado exitosamente.",
            "data": extracted_data
        },
        status=status.HTTP_200_OK
    )
