from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    load_keywords
)

def scraper_ncbi(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    keywords = load_keywords("plants.txt")

    
    try:
        driver.get(url)
        for term in keywords:
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
                    all_scraper += table_data + "\n"
            except:
                continue

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
