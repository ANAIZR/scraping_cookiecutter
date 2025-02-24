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

def close_modal(driver):
    try:
        close_button = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a.header-action.action-close")
            )
        )
        driver.execute_script("arguments[0].click();", close_button)
    except Exception as e:
        print(f"No se pudo cerrar el modal: {e}")

def scraper_mycobank_org(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    total_scraped_successfully = 0
    
    try:
        driver.get(url)
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#search-btn"))
        )
        driver.execute_script("document.querySelector('#search-btn').click();")
        time.sleep(5)
        
        while True:
            WebDriverWait(driver, 60).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "table.mat-table tbody tr")
                )
            )
            time.sleep(5)
            rows = driver.find_elements(By.CSS_SELECTOR, "table.mat-table tbody tr")

            for index, row in enumerate(rows, start=1):
                try:
                    time.sleep(5)
                    link = row.find_element(By.CSS_SELECTOR, "td a")
                    link_name = link.text.strip()
                    link_href = link.get_attribute("href")
                    driver.execute_script("arguments[0].click();", link)
                    
                    time.sleep(5)
                    popup_title = (
                        WebDriverWait(driver, 60)
                        .until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.mat-dialog-title")
                            )
                        )
                        .text
                    )

                    popup_content = (
                        WebDriverWait(driver, 60)
                        .until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.first-column")
                            )
                        )
                        .text
                    )

                    content_text = f"Title: {popup_title}\nContent:\n{popup_content}\n{'-'*50}\n"
                    all_scraper += content_text
                    
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
                            fs.delete(oldest_version._id)
                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version._id}")

                    
                    close_modal(driver)
                    
                except Exception as e:
                    print(f"Error al procesar la fila {index}: {e}")
                    continue
            if page == 2:
                break

            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next page']")
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(5)
                page += 1  # Incrementa el contador para reflejar el cambio de página
            except Exception as e:
                logger.error("Error al intentar avanzar al siguiente paginador", e)
                break
            """ try:
                next_button = driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label='Next page']"
                )
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(5)
            except Exception as e:
                logger.error("Error al intentar avanzar al siguiente paginador", e)
                break """

        response = process_scraper_data_v2(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response(
            {"error": "Ocurrió un error durante el scraping."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    
    finally:
        driver.quit()
        logger.info("Navegador cerrado")
