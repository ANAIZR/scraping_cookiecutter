from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("INICIANDO EL SCRAPER")


class ScraperState:
    def __init__(self):
        self.all_scraper = ""
        self.processed_links = set()
        self.extracted_count = 0
        self.skipped_count = 0


def wait_for_element(driver, wait_time, locator):

    try:
        return WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(locator)
        )
    except TimeoutException as e:
        logger.error(f"Elemento no encontrado: {locator} - {str(e)}")
        raise


def scrape_table_rows(driver, wait_time, state):

    rows = driver.find_elements(By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody tr")
    for row in rows:
        try:
            link = row.find_element(By.CSS_SELECTOR, "td a").get_attribute("href")
            if link in state.processed_links:
                logger.info(f"Enlace ya procesado: {link}")
                continue

            state.processed_links.add(link)
            driver.get(link)
            process_page(driver, wait_time, state)
        except Exception as e:
            state.skipped_count += 1
            logger.error(f"Error procesando fila: {str(e)}")
    return state


def process_page(driver, wait_time, state):

    try:
        wait_for_element(driver, wait_time, (By.CSS_SELECTOR, "section.container div.rfInv"))
        cards = driver.find_elements(By.CSS_SELECTOR, "div.col-md-2")
        for card in cards:
            link_in_card = card.find_element(By.CSS_SELECTOR, "a")
            link_in_card.click()
            process_card_page(driver, wait_time, state)
    except Exception as e:
        logger.error(f"Error procesando página: {str(e)}")


def process_card_page(driver, wait_time, state):

    original_window = driver.current_window_handle
    new_window = [w for w in driver.window_handles if w != original_window][0]
    driver.switch_to.window(new_window)
    try:
        content = wait_for_element(driver, wait_time, (By.CSS_SELECTOR, "main.container div.parteesq")).text
        state.all_scraper += f"Datos extraídos: {content}\n\n"
        state.extracted_count += 1
    finally:
        driver.close()
        driver.switch_to.window(original_window)


def get_current_page_number(driver):

    try:
        page_number_element = driver.find_element(By.CSS_SELECTOR, ".pagination .active a")
        page_number = int(page_number_element.text)
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

    except TimeoutException:
        logger.error("Tiempo de espera agotado al intentar cambiar de página.")
        return False
    except Exception as e:
        logger.error(f"Error al intentar ir a la siguiente página: {str(e)}")
        return False


def scraper_aguiar_hvr(url, sobrenombre):

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    state = ScraperState()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    try:
        driver.get(url)
        while True:
            wait_for_element(
                driver, 30, (By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody")
            )
            current_page = get_current_page_number(driver)
            state = scrape_table_rows(driver, 30, state)

            if not click_next_page(driver, 20):
                break

        response = process_scraper_data(state.all_scraper, url, sobrenombre, collection, fs)
        return response
    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        driver.quit()
