from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
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
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

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

                    content = (
                        f"Title: {popup_title}\nContent:\n{popup_content}\n{'-'*50}\n"
                    )
                    all_scraper += content

                    close_modal(driver)

                except Exception as e:
                    print(f"Error al procesar la fila {index}: {e}")
                    continue
            try:
                next_button = driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label='Next page']"
                )

                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(5)

            except Exception as e:
                print("Error al intentar avanzar al siguiente paginador", e)
                break
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return Response(
            {"error": "Ocurrió un error durante el scraping."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
