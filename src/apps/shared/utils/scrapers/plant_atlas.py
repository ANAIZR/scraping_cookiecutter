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
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    return driver


def get_soup(driver, url):
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "section#partners div.container")
        )
    )
    return BeautifulSoup(driver.page_source, "html.parser")


def process_cards(driver, soup, processed_cards):
    all_scraper_page = []

    containers = soup.select("div.partner-list")
    for container in containers:
        cards = container.select("div.col-lg-3")
        for card in cards:
            try:
                link_card = card.select_one("a")
                if not link_card:
                    continue
                link_card = link_card.get("href")
                if link_card in processed_cards:
                    continue

                title = card.select_one("h3").text
                print(f"Processing card: {title}, Link: {link_card}")
                if link_card:
                    all_scraper_page.extend(scraper_card_page(driver, link_card))

                processed_cards.add(link_card)

            except Exception as e:
                print(f"Error processing card: {e}")

    return all_scraper_page


def scraper_card_page(driver, link_card):
    driver.get(link_card)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#aspnetForm"))
    )

    try:
        btn_selenium = driver.find_element(
            By.ID, "ctl00_cphHeader_ctrlHeader_btnBrowseSearch"
        )
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(btn_selenium))
        btn_selenium.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_cphBody_Grid1"))
        )

        all_scraper_page = []
        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.select_one("#ctl00_cphBody_Grid1")
            if table:
                rows = table.select("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if cols:
                        data = [col.text.strip() for col in cols]
                        all_scraper_page.append(data)

            try:
                next_button = driver.find_element(
                    By.ID, "ctl00_cphBody_Grid1_ctl01_ibNext"
                )
                if next_button.is_enabled():
                    next_button.click()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "#ctl00_cphBody_Grid1")
                        )
                    )
                else:
                    print("No more pages.")
                    break
            except Exception as e:
                print(f"Error during pagination: {e}")
                break

        return all_scraper_page
    except Exception as e:
        print(f"Error processing card page: {e}")
        return []


def save_data_to_file(all_scraper, url, sobrenombre):
    folder_path = generate_directory(url)
    file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(all_scraper)

    return file_path


def save_to_mongodb(file_path, db, collection, fs, url):
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

    response_data = {
        "Tipo": "Web",
        "Url": url,
        "Fecha_scrapper": data["Fecha_scrapper"],
        "Etiquetas": data["Etiquetas"],
        "Mensaje": "Los datos han sido scrapeados correctamente.",
    }
    return response_data


def scraper_plant_atlas(url, sobrenombre):
    driver = None
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scraper = ""

    try:
        driver = init_driver()
        soup = get_soup(driver, url)

        processed_cards = set()
        all_scraper_page = process_cards(driver, soup, processed_cards)

        all_scraper = "\n".join([", ".join(row) for row in all_scraper_page])
        file_path = save_data_to_file(all_scraper, url, sobrenombre)

        response_data = save_to_mongodb(file_path, db, collection, fs, url)

        delete_old_documents(url, collection, fs)

        return Response(
            response_data,
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
