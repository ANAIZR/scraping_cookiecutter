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


def scrape_mode_four(
    url,
    search_button_selector,
    selector,
    attribute,
    content_selector,
    tag_name_first,
    tag_name_second,
    wait_time,
    sobrenombre,
):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    all_scraped = ""
    try:
        driver.get(url)
        search_button = (
            WebDriverWait(driver, wait_time)
            .until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, search_button_selector)
                )
            )
            .find_elements(By.TAG_NAME, tag_name_second)[1]
        )
        search_button.click()

        target_divs = WebDriverWait(driver, wait_time).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
        )
        for div_index, target_div in enumerate(target_divs, start=1):
            urls = target_div.find_elements(By.TAG_NAME, tag_name_second)
            for link_index, link in enumerate(urls, start=1):
                link_href = link.get_attribute(attribute)
                driver.get(link_href)
                pageBody = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, content_selector))
                )
                p_tags = pageBody.find_elements(By.TAG_NAME, tag_name_first)[:5]

                for i, p in enumerate(p_tags, start=1):

                    all_scraped += p.text + "\n"

                driver.back()

                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, search_button_selector)
                    )
                )
        output_dir = r"C:\web_scraping_files"
        folder_path = generate_directory(output_dir, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(all_scraped)

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
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )