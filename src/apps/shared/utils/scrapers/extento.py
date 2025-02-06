from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_extento(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
        )

        tables = driver.find_elements(By.TAG_NAME, "table")
        if len(tables) >= 2:
            second_table = tables[1]
            rows = second_table.find_elements(By.TAG_NAME, "tr")

            if len(rows) >= 2:
                second_row = rows[1]
                tds = second_row.find_elements(By.TAG_NAME, "td")

                first_level_links = [
                    link.get_attribute("href")
                    for td in tds
                    for link in td.find_elements(By.TAG_NAME, "a")
                    if link.get_attribute("href")
                ]

                for href in first_level_links:
                    driver.get(href)

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
                    )

                    new_tables = driver.find_elements(By.TAG_NAME, "table")
                    if len(new_tables) >= 3:
                        third_table = new_tables[2]
                        new_rows = third_table.find_elements(By.TAG_NAME, "tr")

                        second_level_links = [
                            new_link.get_attribute("href")
                            for new_row in new_rows
                            for new_td in new_row.find_elements(By.TAG_NAME, "td")
                            for new_link in new_td.find_elements(By.TAG_NAME, "a")
                            if new_link.get_attribute("href")
                        ]
                        if second_level_links:
                            for new_href in second_level_links:
                                driver.get(new_href)
                                try:
                                    body = WebDriverWait(driver, 30).until(
                                        EC.presence_of_element_located(
                                            (By.TAG_NAME, "body")
                                        )
                                    )
                                    if body:
                                        body_content = body.text
                                        if body_content.strip():
                                            all_scraper += f"URL: {new_href}\n"
                                            all_scraper += f"{body_content}\n\n"

                                    time.sleep(2)
                                finally:
                                    try:
                                        driver.back()
                                        WebDriverWait(driver, 10).until(
                                            EC.presence_of_all_elements_located(
                                                (By.TAG_NAME, "table")
                                            )
                                        )
                                    except WebDriverException as e:
                                        logger.error(
                                            f"Error al regresar a la página anterior: {e}"
                                        )
                    try:
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
                        )
                    except WebDriverException as e:
                        logger.error(
                            f"Error al intentar volver a la página anterior: {e}"
                        )

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado")

