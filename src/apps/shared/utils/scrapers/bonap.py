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
from datetime import datetime
from bson import ObjectId


def scraper_bonap(
    url,
    sobrenombre,
):
    logger = get_logger("scraper")

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    all_scraper = ""
    non_scraped_urls = []  
    scraped_urls = []
    total_scraped_links = 0
    index = 0

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
                    index += 1
                    href = url + f"-{index}"
                    print("href by quma: ", href)
                    species_name = species.text.strip()

                    species.click()
                    time.sleep(2)

                    try:
                        content_div = driver.find_element(By.ID, "view-frame")
                        content = content_div.text.strip()
                        body_content = f"1 : # {family_name} - {genus_name} - {species_name}\nContenido :\n{content}"
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

                    except Exception as e:
                        print(f"    Error al extraer contenido: {e}")


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
