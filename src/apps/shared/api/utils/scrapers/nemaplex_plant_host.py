import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient
import gridfs
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status


def scrape_nemaplex_plant_host(url, sobrenombre):
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
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "DropDownList1"))
        )

        dropdown = Select(driver.find_element(By.ID, "DropDownList1"))

        for index in range(len(dropdown.options)):

            dropdown.select_by_index(index)

            submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
            submit_button.click()
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "GridView1"))
                )

                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                table = page_soup.find("table", {"id": "GridView1"})
                if table:
                    
                    rows = table.find_all("tr")
                    for row in rows:
                        columns = row.find_all("td")
                        row_data = [col.get_text(strip=True) for col in columns]
                        all_scrapped += (
                            " ".join(row_data) + "\n"
                        ) 
                
            except:
                print(f"Error inesperado para la opción {index + 1}. Excepción: {str(e)}")

            driver.back()

            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "DropDownList1"))
            )

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
