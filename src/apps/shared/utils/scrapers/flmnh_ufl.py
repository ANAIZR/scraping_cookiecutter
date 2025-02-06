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


def scraper_flmnh_ufl(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()

    try:
        collection, fs = connect_to_mongo()
    except Exception as e:
        logger.error(f"Error al conectar a MongoDB: {str(e)}")
        return Response(
            {"error": f"Error al conectar a MongoDB: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    all_scraper = f"{url}\n\n"

    def scrape_page():
        nonlocal all_scraper
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "table.x-grid-table tbody tr")
                )
            )
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows = soup.select("table.x-grid-table tbody tr:not(.x-grid-header-row)")

            for row in rows:
                cols = row.find_all("td")
                data = [col.text.strip() for col in cols]
                all_scraper += " | ".join(data) + "\n"  
        except Exception as e:
            logger.error(f"Error durante el scraping de la página: {str(e)}")
            raise e

    def go_to_next_page():
        try:
            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "button-1065-btnEl"))
            )
            next_button = driver.find_element(By.ID, "button-1065-btnEl")
            driver.execute_script("arguments[0].click();", next_button)
            logger.info("Clic en el botón de siguiente página")
            return True
        except Exception as e:
            logger.warning(
                f"No se pudo hacer clic en el botón de siguiente página: {str(e)}"
            )
            return False

    try:
        driver.get(url)
        logger.info(f"URL cargada: {url}")

        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl"))
        )
        btn = driver.find_element(By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl")
        driver.execute_script("arguments[0].click();", btn)

        scrape_page()

        while go_to_next_page():
            time.sleep(2)
            scrape_page()

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado")

