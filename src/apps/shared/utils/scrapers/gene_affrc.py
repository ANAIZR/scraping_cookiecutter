from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from ..functions import (
    get_logger,
    connect_to_mongo,
    initialize_driver,
    process_scraper_data,
)

import time
import random
from selenium.webdriver.support.ui import Select

logger = get_logger("scraper")


def scraper_gene_affrc(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    try:
        driver.get(url)
        wait_time = random.uniform(5, 15)

        checkboxes = WebDriverWait(driver, wait_time).until(
            EC.presence_of_all_elements_located(
                (
                    By.CSS_SELECTOR,
                    "form#search div:nth-child(7) span:nth-child(2) input[type='checkbox']",
                )
            )
        )
        for checkbox in checkboxes:
            if not checkbox.is_selected():
                driver.execute_script("arguments[0].click();", checkbox)

        btn = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "form#search input[type='submit']")
            )
        )
        driver.execute_script("arguments[0].click();", btn)

        pagination_select = Select(driver.find_element(By.ID, "pagination"))
        for page_index in range(1, len(pagination_select.options) + 1):
            try:
                pagination_select.select_by_index(page_index)
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.table-responsive")
                    )
                )

                html_content = driver.page_source
                soup = BeautifulSoup(html_content, "html.parser")

                rows = soup.select("div.table-responsive tbody tr")

                for index, current_row in enumerate(rows):
                    try:
                        second_td = current_row.select_one("td:nth-child(2) a")
                        link = second_td.get("href")
                        driver.execute_script("window.open(arguments[0]);", link)
                        original_window = driver.current_window_handle
                        WebDriverWait(driver, 10).until(
                            lambda d: len(d.window_handles) > 1
                        )
                        new_window = [
                            window
                            for window in driver.window_handles
                            if window != original_window
                        ][0]
                        driver.switch_to.window(new_window)
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.container table.table")
                            )
                        )
                        content = WebDriverWait(driver, wait_time).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.container div>table tbody")
                            )
                        )
                        time.sleep(2)
                        all_scraper += content.text
                        rows = content.find_elements(By.CSS_SELECTOR, "tr")

                        for row in rows:
                            cells = row.find_elements(By.CSS_SELECTOR, "td")
                            headers = row.find_elements(By.CSS_SELECTOR, "th")

                            if headers:
                                for header in headers:
                                    all_scraper += header.text.strip() + ": "

                            for cell in cells:
                                all_scraper += cell.text.strip() + "\n"
                        driver.close()
                        driver.switch_to.window(original_window)

                    except Exception as e:
                        print(f"Error procesando : {e}")
            except Exception as e:
                print(f"Error procesando : {e}")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        print(f"Ocurrió un error: {e}")

    finally:
        driver.quit()
