from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import gridfs
import os
from .functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status
import time
from selenium.webdriver.support.ui import Select


def scrape_gene_affrc(url, sobrenombre, wait_time):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scrapped = ""
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
                print(f"Seleccionando checkbox: {checkbox.get_attribute('value')}")
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
                        print(f"Haciendo clic en el enlace: {link}")
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
                        all_scrapped += content.text
                        rows = content.find_elements(By.CSS_SELECTOR, "tr")

                        for row in rows:
                            cells = row.find_elements(By.CSS_SELECTOR, "td")
                            headers = row.find_elements(By.CSS_SELECTOR, "th")

                            if headers:
                                for header in headers:
                                    all_scrapped += header.text.strip() + ": "

                            for cell in cells:
                                all_scrapped += cell.text.strip() + "\n"
                        driver.close()
                        driver.switch_to.window(original_window)

                    except Exception as e:
                        print(f"Error procesando : {e}")
            except Exception as e:
                print(f"Error procesando : {e}")

        output_dir = r"C:\web_scraping_files"
        folder_path = generate_directory(output_dir, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(all_scrapped)

        with open(file_path, "rb") as file_data:
            object_id = fs.put(file_data, filename=os.path.basename(file_path))

            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            response_data = {
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": data["Fecha_scrapper"],
                "Etiquetas": data["Etiquetas"],
                "Mensaje": "Los datos han sido scrapeados correctamente.",
            }

            collection.insert_one(data)
            delete_old_documents(url, collection, fs)
        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        print(f"Ocurrió un error: {e}")

    finally:
        driver.quit()
