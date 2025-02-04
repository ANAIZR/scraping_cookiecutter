from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    load_keywords,
)


def scraper_index_fungorum(url, sobrenombre):
    logger = get_logger("scraper")

    search_terms = load_keywords("fungi.txt")
    logger.info(f"Iniciando scraping para URL: {url}")

    if not search_terms:
        logger.error("No se encontraron palabras")

        return Response(
            {"error": "No se encontraron términos para buscar."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    try:
        driver.get(url)

        for term in search_terms:
            try:
                input_field = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "SearchTerm"))
                )

                input_field.clear()
                input_field.send_keys(term)

                btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                btn.click()
                time.sleep(4)

                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mainbody"))
                )
                time.sleep(8)

                links = driver.find_elements(By.CSS_SELECTOR, "a.LinkColour1")

                if not links:
                    continue

                for index, link in enumerate(links, start=1):
                    href = link.get_attribute("href")
                    text = link.text.strip()

                    driver.get(href)
                    main = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "table.mainbody")
                        )
                    )

                    try:
                        content = main.text
                        # Concatenar el contenido junto con la URL
                        all_scraper += f"URL: {href}\nContenido:\n{content}\n\n"
                    except Exception as e:
                        logger.error(f"Error al procesar contenido de {href}: {str(e)}")

                    driver.back()
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "table.mainbody")
                        )
                    )

                input_field = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "SearchTerm"))
                )
                input_field.clear()

            except Exception as selee:
                logger.error(f"Error al procesar el término '{term}': {str(selee)}")
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error general en el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
