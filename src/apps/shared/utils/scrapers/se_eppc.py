from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
from urllib.parse import urljoin
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_se_eppc(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    try:
        driver.get(url)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.content1 table tbody"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tr_tags = soup.select("div.content1 table tbody tr")

        for index, tr in enumerate(tr_tags[1:], start=2):
            try:
                first_td = tr.select_one("td:first-child a")
                if first_td:
                    href = first_td.get("href")
                    if not href.startswith("http"):
                        href = urljoin(url, href)  

                    logger.info(f"Accediendo a: {href}")
                    driver.get(href)
                    time.sleep(5)

                    nav_fact_sheets = WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.container ul.nav li:nth-child(1)")
                        )
                    )
                    nav_fact_sheets.click()
                    time.sleep(5)

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    content = soup.select_one("#overview")

                    if content:
                        page_text = content.text.strip()
                        all_scraper += f"\n\nURL: {href}\n{page_text}\n"
                    else:
                        logger.warning(f"No se encontró contenido en la URL: {href}")

            except Exception as e:
                logger.error(f"Error al procesar el enlace {href}: {e}")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
