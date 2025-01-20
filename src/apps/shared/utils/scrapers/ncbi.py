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
)

def scraper_ncbi(url, sobrenombre):
    logger = get_logger("scraper", sobrenombre)
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

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
                    all_scraper += table_data + "\n"
            except:
                continue

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
