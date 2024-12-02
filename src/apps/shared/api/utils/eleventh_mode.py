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


def scrape_eleventh_mode(
    url,
    content_selector_third,
    content_selector_fourth,
    content_selector_fifth,
    tag_name_fourth,
    sobrenombre,
    attribute,
    content_selector,
    content_selector_second,
    selector,
    tag_name_first,
    tag_name_second,
    search_button_selector,
):
    driver = None
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scrapper = ""
    try:
        driver.get(url)

        processed_cards = set()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, content_selector_third))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        section = soup.select_one(content_selector_third)
        if section:
            containers = section.select(content_selector_fourth)
            for container in containers:
                cards = container.select(content_selector_fifth)
                for card in cards:
                    link_card = card.select_one(tag_name_fourth).get(attribute)
                    if link_card in processed_cards:
                        continue

                    try:
                        title = card.select_one("h3").text
                        link_card = card.select_one("a").get("href")
                        print(f"Processing card: {title}, Link: {link_card}")
                        if link_card:
                            driver.get(link_card)
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, content_selector)
                                )
                            )

                            try:
                                btn_selenium = driver.find_element(
                                    By.ID, content_selector_second
                                )
                                WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable(btn_selenium)
                                )
                                btn_selenium.click()
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, selector)
                                    )
                                )

                                all_scrapper_page = []
                                while True:
                                    soup = BeautifulSoup(
                                        driver.page_source, "html.parser"
                                    )
                                    table = soup.select_one(selector)
                                    if table:
                                        rows = table.select(tag_name_first)
                                        for row in rows:
                                            cols = row.find_all(tag_name_second)
                                            if cols:
                                                data = [
                                                    col.text.strip() for col in cols
                                                ]
                                                all_scrapper_page.append(data)

                                    try:
                                        next_button = driver.find_element(
                                            By.ID, search_button_selector
                                        )
                                        if next_button.is_enabled():
                                            next_button.click()
                                            WebDriverWait(driver, 10).until(
                                                EC.presence_of_element_located(
                                                    (By.CSS_SELECTOR, selector)
                                                )
                                            )
                                        else:
                                            print("No more pages.")
                                            break
                                    except Exception as e:
                                        print(f"Error during pagination: {e}")
                                        break

                                all_scrapper += (
                                    "\n".join(
                                        [", ".join(row) for row in all_scrapper_page]
                                    )
                                    + "\n"
                                )
                            except Exception as e:
                                print(f"Button not found or not clickable: {e}")
                    except Exception as e:
                        print(f"Error processing card: {e}")

                    processed_cards.add(link_card)

        output_dir = r"C:\web_scraping_files"
        folder_path = generate_directory(output_dir, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)
        folder_path = generate_directory(output_dir, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(all_scrapper)

        with open(file_path, "rb") as file_data:
            object_id = fs.put(file_data, filename=os.path.basename(file_path))

        # Guardamos en la base de datos MongoDB
        data = {
            "Objeto": object_id,
            "Tipo": "Web",
            "Url": url,
            "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["planta", "plaga"],
        }
        collection = db["collection"]
        collection.insert_one(data)

        # Elimina documentos antiguos
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
    finally:
        if driver:
            driver.quit()
