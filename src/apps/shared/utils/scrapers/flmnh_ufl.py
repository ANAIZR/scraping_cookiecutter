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


def scraper_flmnh_ufl(
    url,
    sobrenombre,
):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    def scrape_page():
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "table.x-grid-table tbody tr")
            )
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("table.x-grid-table tbody tr:not(.x-grid-header-row)")

        all_scraper_data = []
        for row in rows:
            cols = row.find_all("td")
            data = [col.text.strip() for col in cols]
            all_scraper_data.append(data)

    def go_to_next_page():
        try:
            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "button-1065-btnEl"))
            )

            next_button = driver.find_element(By.ID, "button-1065-btnEl")
            next_button.click()
            return True
        except Exception as e:
            return False

    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl"))
        )
        btn = driver.find_element(By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl")
        btn.click()

        scrape_page()

        while go_to_next_page():
            time.sleep(2)
            scrape_page()

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
