from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
from bs4 import BeautifulSoup
from selenium.common.exceptions import StaleElementReferenceException
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_aphis_usda(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.c-link-list-multi-column")
            )
        )

        while True:
            link_list = driver.find_elements(
                By.CSS_SELECTOR, "div.c-link-list-multi-column ul li a"
            )

            if not link_list:
                break

            new_links_found = False
            for link in link_list:
                href = link.get_attribute("href")

                if href in processed_links:
                    continue

                processed_links.add(href)
                new_links_found = True

                try:
                    driver.get(href)
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.c-wysiwyg")
                        )
                    )

                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    content_div = page_soup.find("div", class_="c-wysiwyg")
                    time.sleep(5)

                    if content_div:
                        content_text = content_div.text.strip()
                        if content_text:
                            all_scraper += content_text + "\n\n"
                        
                    

                except StaleElementReferenceException:
                    print(
                        f"Elemento obsoleto en la página {href}, recargando y volviendo a buscar el enlace."
                    )
                    driver.get(href)
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.c-wysiwyg")
                        )
                    )

                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    content_div = page_soup.find("div", class_="c-wysiwyg")
                    time.sleep(5)

                    if content_div:
                        content_text = content_div.text.strip()
                        if content_text:
                            all_scraper += content_text + "\n\n"
                        
                    

                driver.back()
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.c-link-list-multi-column")
                    )
                )

            if not new_links_found:
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        print(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        try:
            driver.quit()
        except Exception as e:
            print(f"Error al cerrar el navegador: {e}")
