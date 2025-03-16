from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    save_to_mongo
)
import time
import random
from datetime import datetime
from bson import ObjectId

def scraper_nemaplex_plant_host(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = driver_init()
    collection, fs = connect_to_mongo()

    all_scraper = ""
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    scraped_urls = set()
    failed_urls = set()
    visited_urls = set()
    object_ids = []

    try:
        driver.get(url)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "DropDownList1"))
        )

        dropdown = Select(driver.find_element(By.ID, "DropDownList1"))

        for i in range(len(dropdown.options)):
            try:
                dropdown = Select(driver.find_element(By.ID, "DropDownList1"))
                option_text = dropdown.options[i].text.strip()
                logger.info(f"📌 Procesando opción {i}: {option_text}")

                total_links_found += 1

                dropdown.select_by_index(i)
                time.sleep(1)

                submit_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']"))
                )
                driver.execute_script("arguments[0].click();", submit_button)

                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)

                result_url = driver.current_url

                if result_url not in visited_urls:
                    visited_urls.add(result_url)
                    scraped_urls.add(result_url)
                    logger.info(f"✅ URL extraída: {result_url}")

                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                table = page_soup.find("table", {"id": "GridView1"})

                if table:
                    content_text = table.get_text(separator="\n", strip=True)
                    logger.info(f"✅ Se encontró tabla con datos para {option_text}")
                else:
                    content_text = "No tiene información disponible"
                    logger.warning(f"⚠️ No se encontró la tabla en {result_url}")

                try:
                    object_id = save_to_mongo("urls_scraper", content_text, result_url, url)  # 📌 Guardar en `urls_scraper`
                    total_scraped_successfully += 1
                    logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")
                    

                except Exception as e:
                    logger.error(f"❌ Error al guardar en MongoDB: {e}")
                    total_failed_scrapes += 1
                    failed_urls.add(result_url)
                    scraped_urls.remove(result_url)

                if option_text == "Abelia spathulata Siebold & Zucc.":
                    logger.info(f"Se encontró '{option_text}'. Deteniendo el scraper.")
                    break

                driver.get(url)
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "DropDownList1"))
                )
                time.sleep(2)

            except Exception as e:
                logger.error(f"❌ Error al extraer datos de la opción {option_text}: {str(e)}")
                total_failed_scrapes += 1
                failed_urls.add(url)
                driver.get(url)
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "DropDownList1"))
                )
                time.sleep(2)
                continue

        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)        
     
        return response


    except Exception as e:
        logger.error(f"⚠️ Error general en el scraper: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("🚪 Navegador cerrado.")