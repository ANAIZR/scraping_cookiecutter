from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
import os
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time


def scrape_bonap(
    url,
    sobrenombre,
):
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")
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
        time.sleep(3)

        family_list = driver.find_elements(By.CSS_SELECTOR, "#family-list li")
        for family in family_list:
            family_name = family.text.strip()
            print(f"Familia: {family_name}")

            family.click()
            time.sleep(2)

            genus_list = driver.find_elements(By.CSS_SELECTOR, "#genus-list li")
            for genus in genus_list:
                genus_name = genus.text.strip()
                print(f"  Género: {genus_name}")

                genus.click()
                time.sleep(2)

                species_list = driver.find_elements(By.CSS_SELECTOR, "#species-list li")
                for species in species_list:
                    species_name = species.text.strip()
                    print(f"    Especie: {species_name}")

                    species.click()
                    time.sleep(2)

                    try:
                        content_div = driver.find_element(By.ID, "view-frame")
                        content = content_div.text.strip()

                        all_scrapped += f"1 : # {family_name} - {genus_name} - {species_name}\nContenido :\n{content}"

                    except Exception as e:
                        print(f"    Error al extraer contenido: {e}")
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
