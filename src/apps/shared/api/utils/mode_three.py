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
from ..utils.functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status


def scrape_mode_three(
    url,
    wait_time,
    search_button_selector,
    content_selector,
    sobrenombre,
    tag_name_one,
    tag_name_second,
    tag_name_third,
    attribute,
    selector,
    next_page_selector,
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
        submit = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    search_button_selector,
                )
            )
        )
        submit.click()
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    content_selector,
                )
            )
        )

        def scrape_page():
            nonlocal all_scrapped
            content= BeautifulSoup(driver.page_source, "html.parser")
            content_container = content.select_one(content_selector)

            tr_tags = content_container.find_all(tag_name_one)

            for i, tr_tag in enumerate(tr_tags):
                
                if is_first_page:
                    if i < 2 or i >= len(tr_tags) - 2:
                        continue
                try:
                    td_tags = tr_tag.select(tag_name_second)
                    if td_tags:
                        a_tags = td_tags[0].find(tag_name_third)
                        if a_tags:

                            print("Ingresando")
                            href = a_tags.get(attribute)
                            page = "http://www.efloras.org/"+href
                            if href:
                                driver.get(page)
                                WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, selector)
                                    )
                                )
                                content = BeautifulSoup(driver.page_source, "html.parser")
                                if content:
                                    all_scrapped += f"Contenido de la página {href}:\n"
                                    all_scrapped+="Ingresooo"
                                    cleaned_text = " ".join(content.text.split()) 
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
                    EC.presence_of_element_located((By.CSS_SELECTOR, next_page_selector))
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
