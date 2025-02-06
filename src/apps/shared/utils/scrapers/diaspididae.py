from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)


def clean_text(text):
    return " ".join(text.split()).strip()


def format_scraper_data_with_headers(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    formatted_text = ""
    for element in soup.find_all(recursive=False):
        if element.name == "b":
            formatted_text += f"\n{element.get_text()}\n"
        elif element.get_text(strip=True):
            formatted_text += f"{element.get_text(separator=' ')} "
    return formatted_text.strip()


def scraper_species(driver, lookupid):
    base_url = "https://diaspididae.linnaeus.naturalis.nl/linnaeus_ng/app/views/species/taxon.php"
    full_url = f"{base_url}?id={lookupid}"

    driver.get(full_url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div#content.taxon-detail")
            )
        )
        content_div = driver.find_element(By.CSS_SELECTOR, "div#content.taxon-detail")
        html_content = content_div.get_attribute("innerHTML")
    except Exception as e:
        return None

    soup = BeautifulSoup(html_content, "html.parser")
    scraped_data = {}

    scraped_data["text"] = format_scraper_data_with_headers(html_content)

    return {
        "url": full_url,  
        "text": scraped_data["text"],
    }


def scraper_diaspididae(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "p.row"))
        )
        elements = driver.find_elements(By.CSS_SELECTOR, "p.row")
        lookup_ids = [el.get_attribute("lookupid") for el in elements]

        for lookupid in lookup_ids:
            scraped_data = scraper_species(driver, lookupid)
            if scraped_data:
                all_scraper += f"URL: {scraped_data['url']}\n\n"
                all_scraper += f"{scraped_data['text']}\n"
                all_scraper += "\n" + "-" * 80 + "\n\n"  

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado")

