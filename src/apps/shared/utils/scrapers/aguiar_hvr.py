from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("INICIANDO EL SCRAPER")


def wait_for_element(driver, wait_time, locator):
    try:
        return WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(locator)
        )
    except Exception as e:
        logger.error(f"Error esperando el elemento: {locator} - {str(e)}")
        raise


def scrape_table_rows(driver, wait_time, all_scraper, processed_links):
    rows = driver.find_elements(By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody tr")
    extracted_count = 0
    skipped_count = 0
    skipped_links = []

    logger.info(f"{len(rows)} filas encontradas en la tabla.")
    for row in rows:
        try:
            first_td = row.find_element(By.CSS_SELECTOR, "td a")
            link = first_td.get_attribute("href")

            if link in processed_links:
                logger.info(f"El enlace ya fue procesado: {link}")
                continue

            processed_links.add(link)
            extracted_count += 1

            logger.info(f"PROCESANDO ENLACE: {link}")
            driver.get(link)
            wait_for_element(
                driver, wait_time, (By.CSS_SELECTOR, "section.container div.rfInv")
            )

            cards = driver.find_elements(By.CSS_SELECTOR, "div.col-md-2")
            for card in cards:
                link_in_card = card.find_element(By.CSS_SELECTOR, "a")
                link_in_card.click()
                original_window = driver.current_window_handle
                all_windows = driver.window_handles
                new_window = [
                    window for window in all_windows if window != original_window
                ][0]
                driver.switch_to.window(new_window)
                try:
                    new_page_content = wait_for_element(
                        driver,
                        wait_time,
                        (By.CSS_SELECTOR, "main.container div.parteesq"),
                    )
                    extracted_text = new_page_content.text
                    if not extracted_text:
                        continue
                    processed_links.add(driver.current_url)
                    logger.info(f"URL visitad:{driver.current_url}")
                    all_scraper += f"Datos extraídos de {driver.current_url}\n"
                    all_scraper += extracted_text + "\n\n"
                    all_scraper += "*************************\n"
                    extracted_count += 1
                    driver.close()
                    driver.switch_to.window(original_window)
                except Exception as e:
                    logger.error(f"Error al procesar una ventana: {str(e)}")
            driver.back()
            time.sleep(2)
            wait_for_element(
                driver,
                wait_time,
                (By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody"),
            )
        except Exception as e:
            skipped_count += 1
            logger.error(f"Error procesando una fila: {str(e)}")

    all_scraper += f"TOTAL ENLACES PROCESADOS: {extracted_count}\n"
    all_scraper += f"TOTAL ENLACES NO PROCESADOS: {skipped_count}\n"
    if skipped_links:
        all_scraper += "ENLACES NO PROCESADOS:\n"
        all_scraper += "\n".join(skipped_links) + "\n"

    logger.info(f"TOTAL DE DATOS EXTRAIDOS: {extracted_count}")
    return all_scraper, extracted_count


def get_current_page_number(driver):
    try:
        page_number_element = driver.find_element(
            By.CSS_SELECTOR, ".pagination .active a"
        )
        page_number = int(page_number_element.text)
        logger.info(f"Página actual: {page_number}")
        return page_number
    except Exception as e:
        logger.error(f"No se pudo obtener el número de página actual: {str(e)}")
        return None


def click_next_page(driver, wait_time):
    try:
        next_button = wait_for_element(
            driver, wait_time, (By.CSS_SELECTOR, "#DataTables_Table_0_next a")
        )
        if "disabled" in next_button.get_attribute("class"):
            return False

        current_page = get_current_page_number(driver)
        next_button.click()

        WebDriverWait(driver, wait_time).until(
            lambda d: get_current_page_number(d) != current_page
        )
        wait_for_element(
            driver, wait_time, (By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody")
        )
        return True
    except Exception as e:
        logger.error(f"Error al intentar ir a la siguiente página: {str(e)}")
        return False


def scraper_aguiar_hvr(url, wait_time, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()

    try:
        driver.get(url)
        while True:
            wait_for_element(
                driver,
                wait_time,
                (By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody"),
            )

            current_page = get_current_page_number(driver)

            all_scraper, extracted_count = scrape_table_rows(
                driver, wait_time, all_scraper, processed_links
            )
            logger.info(
                f"Datos extraídos en la página {current_page}: {extracted_count}"
            )

            if not click_next_page(driver, wait_time):
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
