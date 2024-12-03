from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
import os
from datetime import datetime
from .functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status
import time

def scrape_eighth_mode(
    url,
    wait_time,
    content_selector,
    selector,
    tag_name_first,
    attribute,
    content_selector_second,
    content_selector_third,
    tag_name_second,
    content_selector_fourth,
    content_selector_fifth,
    attribute_second,
    sobrenombre
):
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    output_dir = r"C:\web_scraping_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_scrapped = ""

    try:
        driver.get(url)

        while True:
            try:
                content = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, content_selector))
                )

                rows = driver.find_elements(By.CSS_SELECTOR, selector)
                for row in rows:
                    first_td = row.find_element(By.CSS_SELECTOR, tag_name_first)
                    link = first_td.get_attribute(attribute)

                    driver.get(link)

                    content = WebDriverWait(driver, wait_time).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, content_selector_second)
                        )
                    )
                    cards = driver.find_elements(
                        By.CSS_SELECTOR, content_selector_third
                    )
                    for card in cards:
                        link_in_card = card.find_element(
                            By.CSS_SELECTOR, tag_name_second
                        )
                        card_href = link_in_card.get_attribute(attribute)
                        link_in_card.click()

                        original_window = driver.current_window_handle
                        all_windows = driver.window_handles
                        new_window = [
                            window
                            for window in all_windows
                            if window != original_window
                        ][0]
                        driver.switch_to.window(new_window)

                        new_page_content = WebDriverWait(driver, wait_time).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, content_selector_fourth)
                            )
                        )
                        extracted_text = new_page_content.text 

                        all_scrapped += f"Datos extraídos de {driver.current_url}\n"
                        all_scrapped += extracted_text + "\n\n"
                        all_scrapped += f"*************************" 
                        driver.close()
                        driver.switch_to.window(original_window)

                    driver.back()
                    time.sleep(2)
                    WebDriverWait(driver, wait_time).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, content_selector)
                        )
                    )

                next_button = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, content_selector_fifth)
                    )
                )

                if "disabled" in next_button.get_attribute(attribute_second):
                    break

                next_button.click()
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, content_selector_fifth)
                    )
                )

            except Exception as e:
                break

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

        print(f"Los datos se han guardado en MongoDB y en el archivo: {file_path}")
        return Response(
            {"message": "Scraping completado y datos guardados en MongoDB."},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
