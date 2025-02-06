from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import os
from rest_framework.response import Response
from rest_framework import status

from ..functions import (
    connect_to_mongo,
    initialize_driver,
    save_scraper_data,
    get_logger
)

def scraper_coleoptera_neotropical(url, sobrenombre):    
    logger = get_logger("Inciando scraper")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "body tbody"))
        )
        content = driver.find_element(By.CSS_SELECTOR, "body tbody")

        rows = content.find_elements(By.TAG_NAME, "tr")
        total_rows = len(rows)

        all_scraper = f"Total de filas encontradas: {total_rows}\n"

        scrape_count = 0

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            row_data = [col.text.strip() for col in cols]  
            all_scraper += ", ".join(row_data) + "\n"  # Concatenar fila al texto acumulado
            scrape_count += 1  

        all_scraper = f"{all_scraper}Filas scrapeadas: {scrape_count}\n"
        response_data = save_scraper_data(all_scraper,url,sobrenombre,collection,fs)
        return response_data

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado")

