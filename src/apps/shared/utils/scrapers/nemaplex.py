from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

import time

def scraper_nemaplex(url, sobrenombre):
    logger = get_logger("scraper")

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = "" 
    
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#form1"))
        )

        button = driver.find_element(By.CSS_SELECTOR, "#Button1")
        if button.is_enabled():
            driver.execute_script("arguments[0].click();", button)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#GridView1")
                )
            )
            time.sleep(5)

        table = driver.find_element(By.ID, "GridView1")

        rows = table.find_elements(By.TAG_NAME, "tr")
        
        for index, row in enumerate(rows):
            columns = row.find_elements(By.TAG_NAME, "td")
            row_data = " | ".join([col.text.strip() for col in columns]) 
            all_scraper += row_data + "\n" 


        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response
    
    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
