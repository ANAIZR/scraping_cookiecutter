from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status
import time

logger = get_logger("scraper")


def scraper_bonap(
    url,
    sobrenombre,
):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    all_scraper = ""

    try:
        driver.get(url)
        time.sleep(3)

        family_list = driver.find_elements(By.CSS_SELECTOR, "#family-list li")
        for family in family_list:
            family_name = family.text.strip()

            family.click()
            time.sleep(2)

            genus_list = driver.find_elements(By.CSS_SELECTOR, "#genus-list li")
            for genus in genus_list:
                genus_name = genus.text.strip()

                genus.click()
                time.sleep(2)

                species_list = driver.find_elements(By.CSS_SELECTOR, "#species-list li")
                for species in species_list:
                    species_name = species.text.strip()

                    species.click()
                    time.sleep(2)

                    try:
                        content_div = driver.find_element(By.ID, "view-frame")
                        content = content_div.text.strip()

                        all_scraper += f"1 : # {family_name} - {genus_name} - {species_name}\nContenido :\n{content}"

                    except Exception as e:
                        print(f"    Error al extraer contenido: {e}")
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
