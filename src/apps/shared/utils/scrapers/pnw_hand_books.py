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
import random


def scraper_pnw_hand_books(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    try:
        driver.get(url)

        def scrape_current_page():
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div.view-content")
                    )
                )
                containers = driver.find_elements(
                    By.CSS_SELECTOR, "div.view-content div.views-row"
                )

                for container in containers:
                    link = container.find_element(
                        By.CSS_SELECTOR, "div.views-field-title a"
                    )
                    href = link.get_attribute("href")
                    logger.info(f"Procesando página: {href}")
                    driver.get(href)
                    time.sleep(random.randint(1, 3))
                    soup = BeautifulSoup(driver.page_source, "html.parser")

                    title = soup.find("h1")
                    content = soup.find("div", class_="region-content")
                    all_scraper += f"URL:{href}\n\n{title.text}\n{content.text}\n"
                    driver.back()
                    time.sleep(2)

            except Exception as e:
                print(f"Error al procesar la página actual: {e}")

        def go_to_next_page():
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "li.next a")
                driver.execute_script("arguments[0].click();", next_button)

                time.sleep(3)
                return True
            except Exception as e:
                print("No se encontró el botón 'Next'. Fin de la paginación.")
                return False

        try:
            time.sleep(5)
            button = driver.find_element(
                By.CSS_SELECTOR, "#edit-submit-plant-subarticles-autocomplete"
            )
            driver.execute_script("arguments[0].click();", button)
            time.sleep(random.randint(1, 3))

            while True:
                scrape_current_page()

                if not go_to_next_page():
                    break

        except Exception as e:
            print(f"Error durante el proceso de scraping: {e}")
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
