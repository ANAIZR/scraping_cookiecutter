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

import os

import os

def scrape_ncbi(url, sobrenombre):
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

    base_dir = os.path.dirname(os.path.abspath(__file__))  
    txt_file_path = os.path.join(base_dir, "..", "txt", "fungi.txt") 
    txt_file_path = os.path.normpath(txt_file_path)

    if not os.path.exists(txt_file_path):
        return Response({"error": f"El archivo {txt_file_path} no existe."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        driver.get(url)

        with open(txt_file_path, 'r') as file:
            search_terms = file.readlines()

        for term in search_terms:
            term = term.strip() 
            if not term:
                continue  

            search_box = driver.find_element(By.ID, "searchtxt")
            search_box.clear()
            search_box.send_keys(term)

            submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
            submit_button.click()

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            try:
                table = driver.find_element(By.XPATH, "//table[@width='100%']")
                table_data = table.text
                if table_data.strip():  
                    all_scrapped += table_data + "\n"
            except:
                continue

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
