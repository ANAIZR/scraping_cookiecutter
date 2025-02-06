from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
from urllib.parse import urljoin
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
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""

    try:
        while url:
            driver.get(url)
            all_scraper = f"{url}\n\n"
            soup = BeautifulSoup(driver.page_source, "html.parser")

            h3_tags = soup.find_all("h3")
            if len(h3_tags) >= 3:
                third_h3 = h3_tags[2]
                for element in third_h3.find_all_next():
                    if element.name in ["p", "h3"]:
                        all_scraper += element.text.strip() + "\n"

            next_link = soup.find("a", text="Siguiente")
            if next_link and "href" in next_link.attrs:
                url = urljoin(url, next_link["href"])  
                logger.info(f"Navegando al siguiente enlace: {url}")
            else:
                logger.info("No se encontró el enlace 'Siguiente'. Finalizando scraping.")
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
