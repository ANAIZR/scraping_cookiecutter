from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    save_to_mongo
)
from datetime import datetime
from bson import ObjectId

def scraper_eppo(
    url,
    sobrenombre,
):
    non_scraped_urls = []  
    scraped_urls = []
    total_scraped_links = 0

    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    try:
        driver.get(url)
        time.sleep(2)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#dttable tbody tr"))
        )
        while True:
            rows = driver.find_elements(By.CSS_SELECTOR, "#dttable tbody tr")

            for i in range(len(rows)):
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, "#dttable tbody tr")
                    row = rows[i]

                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 1:
                        second_td = cells[1]
                        a_tag = second_td.find_element(By.TAG_NAME, "a")
                        href = a_tag.get_attribute("href")

                        if href:
                            driver.get(href)

                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (
                                        By.CSS_SELECTOR,
                                        "div.row>div.col-md-12>div.row>div.col-md-9",
                                    )
                                )
                            )
                            time.sleep(5)
                            page_source = driver.page_source
                            soup = BeautifulSoup(page_source, "html.parser")

                            content = soup.select_one(
                                "div.row>div.col-md-12>div.row>div.col-md-9"
                            )
                            if content:
                                # all_scraper += content.get_text() + "\n"
                                page_text = content.get_text()
                                if page_text:
                                    object_id = save_to_mongo("urls_scraper", page_text, href, url)
                                    total_scraped_links += 1
                                    scraped_urls.append(href)
                                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                    
                                else:
                                    non_scraped_urls.append(href)


                            time.sleep(5)
                            driver.back()

                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "#dttable tbody tr")
                                )
                            )
                        
                except Exception as e:
                    print(f"Error al procesar la fila o hacer clic en el enlace: {e}")
            break
        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre,collection)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
