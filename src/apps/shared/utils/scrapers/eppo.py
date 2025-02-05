from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_eppo(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    try:
        driver.get(url)
        time.sleep(2)
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#dttable tbody tr"))
        )

        while True:
            rows = driver.find_elements(By.CSS_SELECTOR, "#dttable tbody tr")

            for i in range(len(rows)):
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, "#dttable tbody tr")
                    row = rows[i]

                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 1:
                        second_td = cells[1]
                        a_tag = second_td.find_element(By.TAG_NAME, "a")
                        href = a_tag.get_attribute("href")

                        if href:
                            driver.get(href)

                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "div.row>div.col-md-12>div.row>div.col-md-9")
                                )
                            )
                            time.sleep(5)

                            page_source = driver.page_source
                            soup = BeautifulSoup(page_source, "html.parser")

                            content = soup.select_one("div.row>div.col-md-12>div.row>div.col-md-9")
                            if content:
                                text_content = content.get_text().strip()
                                all_scraper += f"\n\nURL: {href}\n{text_content}\n"

                            time.sleep(5)
                            driver.back()

                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "#dttable tbody tr")
                                )
                            )

                except Exception as e:
                    logger.error(f"Error al procesar la fila o hacer clic en el enlace: {e}")

            break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
