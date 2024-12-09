from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
from .functions import (
    save_scraped_data,
)
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup


def clean_text(text):
    return " ".join(text.split()).strip()


def format_scraped_data_with_headers(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    formatted_text = ""
    for element in soup.find_all(recursive=False):
        if element.name == "b":
            formatted_text += f"\n{element.get_text()}\n"
        elif element.get_text(strip=True):
            formatted_text += f"{element.get_text(separator=' ')} "
    return formatted_text.strip()


def scrape_species(driver, lookupid):
    base_url = "https://diaspididae.linnaeus.naturalis.nl/linnaeus_ng/app/views/species/taxon.php"
    full_url = f"{base_url}?id={lookupid}"

    driver.get(full_url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div#content.taxon-detail")
            )
        )
        content_div = driver.find_element(By.CSS_SELECTOR, "div#content.taxon-detail")
        html_content = content_div.get_attribute("innerHTML")
    except Exception as e:
        return None

    soup = BeautifulSoup(html_content, "html.parser")
    scraped_data = {}

    scraped_data["text"] = format_scraped_data_with_headers(html_content)

    return {
        "text": scraped_data["text"],
    }


def scrape_diaspididae(url, sobrenombre):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scrapped = ""

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "p.row"))
        )
        elements = driver.find_elements(By.CSS_SELECTOR, "p.row")
        lookup_ids = [el.get_attribute("lookupid") for el in elements]

        for lookupid in lookup_ids:
            scraped_data = scrape_species(driver, lookupid)
            if scraped_data:
                all_scrapped += f"{scraped_data['text']}\n\n"
                all_scrapped += "\n\n"
        if all_scrapped.strip():
            response_data = save_scraped_data(
                all_scrapped, url, sobrenombre, collection, fs
            )

            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos para scrapear.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
