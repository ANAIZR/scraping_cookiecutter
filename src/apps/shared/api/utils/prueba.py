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


def scrape_third_mode(
    url=None,
    page_principal=None,
    wait_time=None,
    search_button_selector=None,
    content_selector=None,
    sobrenombre=None,
    tag_name_first=None,
    tag_name_second=None,
    tag_name_third=None,
    attribute=None,
    selector=None,
    next_page_selector=None,
):
    # options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scrapped = ""
    is_first_page = True
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

        def scrape_page():
            nonlocal all_scrapped
            content = BeautifulSoup(driver.page_source, "html.parser")
            content_container = content.select_one(content_selector)

            tr_tags = content_container.find_all(tag_name_first)

            for i, tr_tag in enumerate(tr_tags):

                if is_first_page:
                    if i < 2 or i >= len(tr_tags) - 2:
                        continue
                try:
                    td_tags = tr_tag.select(tag_name_second)
                    if td_tags:
                        a_tags = td_tags[0].find(tag_name_third)
                        if a_tags:

                            href = a_tags.get(attribute)
                            page = page_principal + href
                            if href:
                                driver.get(page)
                                WebDriverWait(driver, wait_time).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, selector)
                                    )
                                )
                                content = BeautifulSoup(
                                    driver.page_source, "html.parser"
                                )
                                content_container = content.select_one(selector)

                                if content_container:
                                    all_scrapped += f"Contenido de la página {href}:\n"
                                    cleaned_text = " ".join(content_container.text.split()) 
                                    all_scrapped += cleaned_text + "\n\n"
                                else:
                                    print(f"No content found for page: {href}")
                                driver.back()
                    else:
                        print(f"No se encontraron td_tags en fila {i}.")
                except Exception as e:
                    print(f"Error procesando la fila {i}: {e}")

        scrape_page()
        is_first_page = False

        if next_page_selector:
            try:
                next_page_button = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, next_page_selector)
                    )
                )
                next_page_button.click()
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, content_selector))
                )
                scrape_page()
            except Exception as e:
                print(f"Error al navegar a la siguiente página: {e}")

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
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
