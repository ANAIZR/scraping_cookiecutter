from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import random
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status

# Funciones externas
from ..functions import (
    initialize_driver,
    get_logger,
    connect_to_mongo,
    extract_text_from_pdf,
    load_keywords,
    process_scraper_data  # Importamos la función para procesar y guardar los datos
)

def scraper_search_usa_gov(url, sobrenombre):
    logger = get_logger("ERS")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    # processed_links = set()
    # urls_to_scrape = [(url, 1)]  
    # non_scraped_urls = []  

    # total_found_links = 0
    # total_scraped_links = 0
    # total_non_scraped_links = 0

    def scrape_pages(url, sobrenombre):
        driver = initialize_driver()
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        
        processed_links = set()
        all_scraper = ""
        keywords = load_keywords("plants.txt")
        
        for keyword in keywords:
            search_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "query")))
            search_input.clear()
            search_input.send_keys(keyword)
            search_input.submit()
            time.sleep(random.uniform(3, 6))
            # search_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search-button")))
            # search_button.click()
            
            while True:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                result_divs = soup.select("div.content-block-item.result")
                
                for div in result_divs:
                    link = div.find("a", href=True)
                    if link:
                        full_url = link["href"]
                        if full_url.lower().endswith(".pdf"):
                            if full_url not in processed_links:
                                logger.info(f"Extrayendo texto de PDF: {full_url}")
                                pdf_text = extract_text_from_pdf(full_url)
                                all_scraper += f"\n\nURL: {full_url}\n{pdf_text}\n"
                                processed_links.add(full_url)
                            continue
                        processed_links.add(full_url)
                
                try:
                    next_page_button = driver.find_element(By.CSS_SELECTOR, "a.next_page")
                    next_page_link = next_page_button.get_attribute("href")
                    if next_page_link:
                        driver.get(next_page_link)
                        time.sleep(random.uniform(3, 6))
                    else:
                        break
                except NoSuchElementException:
                    break

        driver.quit()

    
    try:
        all_scraper = scrape_pages(url, sobrenombre)
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
