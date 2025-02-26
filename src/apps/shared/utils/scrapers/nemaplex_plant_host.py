from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
import time
import random

def scraper_nemaplex_plant_host(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    all_scraper = ""
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    scraped_urls = set()
    failed_urls = set()

    try:
        driver.get(url)
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "select#DropDownList1"))
        )

        dropdown = Select(driver.find_element(By.CSS_SELECTOR, "select#DropDownList1"))
        options = dropdown.options

        for option in options:
            text_option = option.text.strip()
            total_links_found += 1  

            if text_option == "Abelia spathulata Siebold & Zucc.":
                print(f"Se ingresó a: {text_option}")
                logger.info(f"Se ingresó a: {text_option}")  
                try:
                    option.click()

                    submit_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='submit']"))
                    )
                    submit_button.click()

                    WebDriverWait(driver, 40).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    table = page_soup.find("table", {"id": "GridView1"})

                    if table:
                        rows = table.find_all("tr")
                        for row in rows:
                            columns = row.find_all("td")
                            row_data = [col.get_text(strip=True) for col in columns]
                            all_scraper += f"{url} | {' '.join(row_data)}\n"
                        total_scraped_successfully += 1
                        scraped_urls.add(url)
                    else:
                        body_content = page_soup.find("body").get_text(strip=True)
                        total_failed_scrapes += 1
                        failed_urls.add(url)

                except Exception as e:
                    logger.error(f"Error al extraer datos de {url}: {str(e)}")
                    total_failed_scrapes += 1
                    failed_urls.add(url)

                time.sleep(5)
                break  

        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error general en el scraper: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
