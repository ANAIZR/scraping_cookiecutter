from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
import os
from rest_framework.response import Response
from rest_framework import status
import time
import random
from ..functions import (
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
urls_to_scrape = []  
non_scraped_urls = []  
scraped_urls = []

def load_search_terms(file_path):
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except Exception as e:
        print(f"Error al cargar términos: {e}")
        return []


def scraper_index_fungorum(url, sobrenombre):
    search_terms = load_search_terms(
        os.path.join(os.path.dirname(__file__), "../txt/plants.txt")
    )

    if not search_terms:
        return Response(
            {"error": "No se encontraron términos para buscar."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
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

                time.sleep(random.uniform(3, 6))
                logger.info(f"Realizando búsqueda con la palabra clave: {term}")

                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mainbody"))
                )
                time.sleep(random.uniform(3, 6))
                logger.info("Búsqueda realizada con éxito")

                number_page = 1
                while True:

                    links = driver.find_elements(By.CSS_SELECTOR, "a.LinkColour1")
                    if not links:
                        continue

                    for link in links:
                        href = link.get_attribute("href")
                        if "NamesRecord" in href:
                            urls_to_scrape.append(href)
                            print("href by qumadev", href)

                    try:
                        print("inicio de capturar el boton de next")
                        next_link = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'[Next >>]')]"))
                        )
                        next_page_link = next_link.get_attribute("href")

                        if next_page_link:
                            next_link.click()
                            time.sleep(random.uniform(3,6))
                            number_page += 1
                            print(f"=========================== Siguiente página: {number_page} ===========================")
                            driver.get(next_page_link)
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "table.mainbody"))
                            )
                        else:
                            print("No more pages.")
                            break
                    except (TimeoutException, NoSuchElementException):
                        break
                        print("next_link by quma", next_link)

                        """ if next_link:
                            number_page += 1
                            print(f"=========================== Siguiente pagina: {number_page} ===========================")
                            next_page_link = next_link.get_attribute("href")
                            driver.get(next_page_link)

                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "table.mainbody")
                                )
                            )
                        else:
                            print("No more pages.")
                            break """
                    except Exception as e:
                        print(f"Error during pagination: {e}")
                        break

                    input_field = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.NAME, "SearchTerm"))
                    )
                    input_field.clear()  

            except Exception as e:
                pass


        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response


    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
