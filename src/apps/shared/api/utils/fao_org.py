from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import gridfs
from .functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup


def scrape_fao_org(
    url,
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

    all_scrapped = ""
    try:
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        h3_tags = soup.find_all("h3")
        if len(h3_tags) >= 3:
            third_h3 = h3_tags[2]
            for element in third_h3.find_all_next():
                if element.name in ["p", "h3"]:
                    all_scrapped += element.text.strip() + "\n"

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
    finally:
        driver.quit()
