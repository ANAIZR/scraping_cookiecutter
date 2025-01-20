from selenium.webdriver.support import expected_conditions as EC
from ..functions import save_scraper_data
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_fao_org(
    url,
    sobrenombre,
):
    logger = get_logger("scraper",sobrenombre)
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    try:
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        h3_tags = soup.find_all("h3")
        if len(h3_tags) >= 3:
            third_h3 = h3_tags[2]
            for element in third_h3.find_all_next():
                if element.name in ["p", "h3"]:
                    all_scraper += element.text.strip() + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response
    finally:
        driver.quit()
