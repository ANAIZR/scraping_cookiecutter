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


def scrape_pest_alerts(
    url,
    selector,
    content_selector,
    tag_name_first,
    tag_name_second,
    attribute,
    content_selector_second,
    sobrenombre,
):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
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
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

        rows = driver.find_elements(By.CSS_SELECTOR, content_selector)

        original_window = driver.current_window_handle

        for row in rows:
            try:
                second_td = row.find_elements(By.TAG_NAME, tag_name_first)[1]
                a_tag = second_td.find_element(By.TAG_NAME, tag_name_second)
                href = a_tag.get_attribute(attribute)
                if href:
                    if href.startswith("/"):
                        href = url + href[1:]

                    print(f"Haciendo clic en el enlace: {href}")

                    driver.execute_script("window.open(arguments[0]);", href)

                    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

                    new_window = driver.window_handles[1]
                    driver.switch_to.window(new_window)

                    WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, content_selector_second)
                        )
                    )

                    content_elements = driver.find_elements(
                        By.CSS_SELECTOR, content_selector_second
                    )
                    if len(content_elements) == 2:
                        content = (
                            content_elements[0].text + "\n" + content_elements[1].text
                        )  
                        all_scrapped += content

                    driver.close()

                    driver.switch_to.window(original_window)

                    time.sleep(2)

            except Exception as e:
                print(f"Error al procesar la fila o hacer clic en el enlace: {e}")
        if all_scrapped.strip():
                folder_path = generate_directory(output_dir, url)
                file_path = get_next_versioned_filename(
                    folder_path, base_name=sobrenombre
                )

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
        else:
                return Response(
                    {"message": "No se encontró contenido para guardar."},
                    status=status.HTTP_204_NO_CONTENT,
                )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
