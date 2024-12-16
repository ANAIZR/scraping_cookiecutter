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


def load_search_terms(file_path):
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except Exception as e:
        print(f"Error al cargar términos: {e}")
        return []


def scraper_index_fungorum(url, sobrenombre):
    search_terms = load_search_terms(
        os.path.join(os.path.dirname(__file__), "../txt/fungi.txt")
    )

    if not search_terms:
        return Response(
            {"error": "No se encontraron términos para buscar."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    all_scraper = ""
    try:
        driver.get(url)

        for term in search_terms:
            try:

                input_field = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "SearchTerm"))
                )

                input_field.clear()

                input_field.send_keys(term)

                btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                btn.click()
                time.sleep(4)

                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mainbody"))
                )
                time.sleep(8)

                links = driver.find_elements(By.CSS_SELECTOR, "a.LinkColour1")

                if not links:
                    continue

                for index, link in enumerate(links, start=1):
                    href = link.get_attribute("href")
                    text = link.text.strip()

                    driver.get(href)
                    main = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "table.mainbody")
                        )
                    )

                    try:
                        content = main.text
                        all_scraper += content
                    except Exception as e:
                        pass

                    driver.back()
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "table.mainbody")
                        )
                    )  

                input_field = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "SearchTerm"))
                )
                input_field.clear()  

            except Exception as e:
                pass
        if all_scraper.strip():
            response_data = save_scraped_data(
                all_scraper, url, sobrenombre, collection, fs
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
