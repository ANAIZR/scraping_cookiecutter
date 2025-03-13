from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
from selenium.common.exceptions import  WebDriverException
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from datetime import datetime
from bson import ObjectId

def scraper_extento(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    non_scraped_urls = []  
    scraped_urls = []
    total_scraped_links = 0

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
        )

        tables = driver.find_elements(By.TAG_NAME, "table")
        if len(tables) >= 2:
            second_table = tables[1]
            rows = second_table.find_elements(By.TAG_NAME, "tr")

            if len(rows) >= 2:
                second_row = rows[1]
                tds = second_row.find_elements(By.TAG_NAME, "td")

                first_level_links = [
                    link.get_attribute("href")
                    for td in tds
                    for link in td.find_elements(By.TAG_NAME, "a")
                    if link.get_attribute("href")
                ]

                for href in first_level_links:
                    driver.get(href)

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
                    )

                    new_tables = driver.find_elements(By.TAG_NAME, "table")
                    if len(new_tables) >= 3:
                        third_table = new_tables[2]
                        new_rows = third_table.find_elements(By.TAG_NAME, "tr")

                        second_level_links = [
                            new_link.get_attribute("href")
                            for new_row in new_rows
                            for new_td in new_row.find_elements(By.TAG_NAME, "td")
                            for new_link in new_td.find_elements(By.TAG_NAME, "a")
                            if new_link.get_attribute("href")
                        ]
                        if second_level_links:
                            for new_href in second_level_links:
                                driver.get(new_href)
                                try:
                                    body = WebDriverWait(driver, 30).until(
                                        EC.presence_of_element_located(
                                            (By.TAG_NAME, "body")
                                        )
                                    )
                                    if body:
                                        body_content = body.text
                                        if body_content:
                                            object_id = fs.put(
                                                body_content.encode("utf-8"),
                                                source_url=href,
                                                scraping_date=datetime.now(),
                                                Etiquetas=["planta", "plaga"],
                                                contenido=body_content,
                                                url=url
                                            )
                                            total_scraped_links += 1
                                            scraped_urls.append(href)
                                            logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
        
                                            existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                                            if len(existing_versions) > 1:
                                                oldest_version = existing_versions[-1]
                                                file_id = oldest_version._id  # Esto obtiene el ID correcto
                                                fs.delete(file_id)  # Eliminar la versión más antigua
                                                logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                                        else:
                                            non_scraped_urls.append(href)            

                                    time.sleep(2)
                                finally:
                                    try:
                                        driver.back()
                                        WebDriverWait(driver, 10).until(
                                            EC.presence_of_all_elements_located(
                                                (By.TAG_NAME, "table")
                                            )
                                        )
                                    except WebDriverException as e:
                                        print(
                                            f"Error al regresar a la página anterior: {e}"
                                        )
                    try:
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
                        )
                    except WebDriverException as e:
                        print(f"Error al intentar volver a la página anterior: {e}")

        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
