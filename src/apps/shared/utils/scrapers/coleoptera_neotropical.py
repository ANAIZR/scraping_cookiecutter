from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import logging
from bson import ObjectId
from rest_framework.response import Response
from rest_framework import status

from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    initialize_driver
)

logger = logging.getLogger(__name__)

def scraper_coleoptera_neotropical(url, sobrenombre):
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "body tbody"))
        )
        content = driver.find_element(By.CSS_SELECTOR, "body tbody")

        rows = content.find_elements(By.TAG_NAME, "tr")

        scraped_rows = 0
        failed_rows = 0
        all_scraper_data = []

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            row_data = [col.text.strip() for col in cols]

            if row_data:
                all_scraper_data.append(", ".join(row_data))
                scraped_rows += 1
            else:
                failed_rows += 1

        scraped_text = "\n".join(all_scraper_data)

        if scraped_text:
            object_id = fs.put(
            scraped_text.encode("utf-8"),
            source_url=url,
            scraping_date=datetime.now(),
            Etiquetas=["planta", "plaga"],
            contenido=scraped_text,
            url=url
            )
            existing_versions = list(fs.find({"source_url": url}).sort("scraping_date", -1))

            if len(existing_versions) > 1:
                oldest_version = existing_versions[-1]
                fs.delete(oldest_version._id)  
                logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version.id}")
                        



        report_text = f"Total filas encontradas: {len(rows)}\n"
        report_text += f"Filas scrapeadas: {scraped_rows}\n"
        report_text += f"Filas no scrapeadas: {failed_rows}\n"

        logger.info(f"Contenido almacenado en MongoDB con object_id: {object_id}, filas scrapeadas: {scraped_rows}, filas fallidas: {failed_rows}")

        
        response = process_scraper_data(report_text, url, sobrenombre)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
