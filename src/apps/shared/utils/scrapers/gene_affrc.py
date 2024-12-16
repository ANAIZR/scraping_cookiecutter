from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
import gridfs
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time
from selenium.webdriver.support.ui import Select


def scraper_gene_affrc(url, sobrenombre, wait_time):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scraper = ""
    try:
        driver.get(url)
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

        if all_scraper.strip():
            response_data = save_scraped_data(
                all_scraper, url, sobrenombre, collection, fs
            )

            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos para scrapear.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )

    except Exception as e:
        print(f"Ocurrió un error: {e}")

    finally:
        driver.quit()
