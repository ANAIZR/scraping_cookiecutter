from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
from bs4 import BeautifulSoup  # Importar BeautifulSoup
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time


def scrape_eppo_quarentine(url, sobrenombre):
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

        # Esperar a que el contenedor esté presente
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.main-content div.container"))
        )

        page_source = driver.page_source

        soup = BeautifulSoup(page_source, "html.parser")

        rows = soup.select("div.main-content div.container div.row")

        if len(rows) >= 4:
            fourth_row = rows[3]  

            table_responsive_divs = fourth_row.select("div.table-responsive")

            for table in table_responsive_divs:
                trs = table.select("tr")

                for tr in trs:
                    tds = tr.select("td em")
                    for em in tds:
                        link = em.find("a")["href"] if em.find("a") else None
                        if link:
                            print(f"Enlace encontrado: {link}")
                            driver.get(link)

                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.col-md-6.col-sm-6.col-xs-6"))
                            )

                            page_source_inner = driver.page_source

                            soup_inner = BeautifulSoup(page_source_inner, "html.parser")

                            content = soup_inner.select("div.col-md-6.col-sm-6.col-xs-6")

                            for item in content:
                                all_scrapped += item.get_text(strip=True) + "\n"
                                print(f"Contenido extraído: {item.get_text(strip=True)}")

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
        print(f"Error en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
