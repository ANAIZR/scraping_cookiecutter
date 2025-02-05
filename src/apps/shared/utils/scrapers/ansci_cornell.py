from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    initialize_driver,
    connect_to_mongo,
    get_logger,
    process_scraper_data,
)
from rest_framework.response import Response
from rest_framework import status
import random
import time
def scraper_ansci_cornell(
    url,
    sobrenombre,
):
    logger = get_logger("ANSCI_CORNELL")

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()

    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    try:
        driver.get(url)
        logger.info(f"Ingresamos a la URL {url}")
        logger.info("Buscaremos el boton")
        time.sleep(random.randint(1, 3))
        search_button = (
            WebDriverWait(driver, 30)
            .until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
                )
            )
            .find_elements(By.TAG_NAME, "a")[1]
        )
        driver.execute_script("arguments[0].click();", search_button)
        print("Dimos click")

        target_divs = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
            )
        )

        for div_index, target_div in enumerate(target_divs, start=1):
            urls = target_div.find_elements(By.TAG_NAME, "a")
            for link_index, link in enumerate(urls, start=1):
                link_href = link.get_attribute("href")
                driver.get(link_href)

                pageBody = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#mainContent #pagebody #main")
                    )
                )

                p_tags = pageBody.find_elements(By.TAG_NAME, "p")[:5]
                for i, p in enumerate(p_tags, start=1):
                    all_scraper += f"URL: {link_href}\n{p.text}\n"

                nested_links = pageBody.find_elements(By.TAG_NAME, "a")
                for nested_link_index, nested_link in enumerate(nested_links, start=1):
                    nested_href = nested_link.get_attribute("href")
                    if nested_href:
                        driver.get(nested_href)
                        
                        nested_page_body = WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "#mainContent #pagebody #main")
                            )
                        )
                        nested_p_tags = nested_page_body.find_elements(By.TAG_NAME, "p")[:5]
                        for nested_p in nested_p_tags:
                            all_scraper += f"URL: {nested_href}\n{nested_p.text}\n"
                        
                        driver.back()

                all_scraper += "**********\n"

                driver.back()
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
                    )
                )

        # Procesa los datos extraídos
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        driver.quit()
