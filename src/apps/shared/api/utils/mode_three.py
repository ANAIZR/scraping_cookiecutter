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
    search_button_selector,
    content_selector,
    tag_name_one,
    wait_time,
    sobrenombre,
    tag_name_second,
    tag_name_third,
    attribute,
    selector,

):
    # options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    try:
        driver.get(url)
        search_button = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, search_button_selector))
        )
        search_button.click()

        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, content_selector))
        )

        content = driver.find_element(By.CSS_SELECTOR, content_selector)
        tr_tags = content.find_elements(By.TAG_NAME, tag_name_one)

        for i, tr_tag in enumerate(tr_tags):
            if i < 2 or i >= len(tr_tags) - 2:
                continue
            try:
                content = driver.find_element(By.CSS_SELECTOR, content_selector)
                tr_tags = content.find_elements(By.TAG_NAME, tag_name_one)
                tr_tag = tr_tags[i]
                td_tags = tr_tag.find_elements(By.TAG_NAME, tag_name_second)
                print(td_tags.text)
                if len(td_tags) >= 2:
                    second_td = td_tags[1]
                    a_tag = second_td.find_element(By.TAG_NAME, tag_name_third)
                    print(a_tag.text)
                    if a_tag:
                        href = a_tag.get_attribute(attribute)
                        text = a_tag.text

                        print(f"Enlace: {href}, Texto: {text}")

                        driver.get(href)
                        WebDriverWait(driver, wait_time).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )

                        page_soup = BeautifulSoup(driver.page_source, "html.parser")
                        content_Box = page_soup.find(selector)

                        if content_Box:
                            all_scrapped += f"Enlace: {href}, Texto: {text}\n"
                            all_scrapped += f"Contenido de la página {href}:\n"
                            all_scrapped += content.get_text(strip=True) + "\n\n"

                        driver.back()
                        WebDriverWait(driver, wait_time).until(
                            EC.presence_of_element_located(
                                (
                                    By.CSS_SELECTOR,
                                    content_selector,
                                )
                            )
                        )
            except Exception as e:
                print(f"Error procesando la fila {i}: {e}")

        soup = BeautifulSoup(driver.page_source, "html.parser")
        text_content = soup.get_text(separator="\n", strip=True)
        output_dir = r"C:\web_scraping_files"
        folder_path = generate_directory(output_dir, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(text_content)

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
