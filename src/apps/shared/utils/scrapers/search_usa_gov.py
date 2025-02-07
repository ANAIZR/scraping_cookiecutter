from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import random
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from datetime import datetime
from PyPDF2 import PdfReader
import requests

# Funciones externas
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
    get_logger,
    connect_to_mongo,
    extract_text_from_pdf
)

logger = get_logger("scraper")


def scraper_search_usa_gov(url, keywords):
    driver = initialize_driver()
    driver.get(url)
    time.sleep(random.uniform(6, 10))
    
    processed_links = set()
    all_scraper = ""
    
    for keyword in keywords:
        search_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "query")))
        search_input.clear()
        search_input.send_keys(keyword)
        search_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search-button")))
        search_button.click()
        time.sleep(random.uniform(3, 6))
        
        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            result_links = soup.select("#srp-results-list a")
            
            for link in result_links:
                full_url = link.get("href")
                if full_url:
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
    return all_scraper
