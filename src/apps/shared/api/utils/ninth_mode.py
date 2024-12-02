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


def scrape_ninth_mode(
    url,
    selector,
    attribute,
    search_button_selector,
    tag_name_first,
    content_selector,
    content_selector_fourth,
    content_selector_second,
    content_selector_third,
    content_selector_fifth,
    tag_name_second,
    tag_name_third,
    tag_name_fourth,
    sobrenombre,
    wait_time
):
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
                    selector
                )
            )
        )
        for checkbox in checkboxes:
            if not checkbox.is_selected():
                print(f"Seleccionando checkbox: {checkbox.get_attribute(attribute)}")
                driver.execute_script("arguments[0].click();", checkbox)

        btn = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, search_button_selector))
        )
        driver.execute_script("arguments[0].click();", btn)

        pagination_select = Select(driver.find_element(By.ID, tag_name_first))
        for page_index in range(1, len(pagination_select.options) + 1):
            try:
                pagination_select.select_by_index(page_index)
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, content_selector))
                )

                html_content = driver.page_source
                soup = BeautifulSoup(html_content, "html.parser")

                rows = soup.select(content_selector_fourth)

                for index, current_row in enumerate(rows):
                    try:
                        second_td = current_row.select_one(content_selector_second)
                        link = second_td.get("href")
                        print(f"Haciendo clic en el enlace: {link}")
                        driver.execute_script("window.open(arguments[0]);", link)
                        original_window = driver.current_window_handle
                        WebDriverWait(driver, 10).until(
                            lambda d: len(d.window_handles) > 1
                        )
                        new_window = [window for window in driver.window_handles if window != original_window][0]
                        driver.switch_to.window(new_window)
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, content_selector_fifth))
                        )
                        content = WebDriverWait(driver, wait_time).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, content_selector_third)
                            )
                        )
                        time.sleep(2)
                        all_scrapped += content.text
                        rows = content.find_elements(By.CSS_SELECTOR, tag_name_second)

                        for row in rows:
                            cells = row.find_elements(By.CSS_SELECTOR, tag_name_third)
                            headers = row.find_elements(By.CSS_SELECTOR, tag_name_fourth)

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

            collection.insert_one(data)
            delete_old_documents(url, collection, fs)
        return Response(
            {"message": "Scraping completado y datos guardados en MongoDB."},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        print(f"Ocurrió un error: {e}")

    finally:
        driver.quit()
