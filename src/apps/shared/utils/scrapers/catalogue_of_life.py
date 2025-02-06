from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    load_keywords
)
from rest_framework.response import Response
from rest_framework import status
import random
import time
from bs4 import BeautifulSoup

logger = get_logger("scraper")





def scraper_catalogue_of_life(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    keywords = load_keywords()
    all_scraper = ""

    try:
        driver.get(url)

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "search_string"))
        )

        for index, keyword in enumerate(keywords):
            all_scraper += f"Palabra clave {index + 1}: {keyword}\n"
            random_wait()

            search_box.clear()
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )

            rows = driver.find_elements(By.XPATH, "//tr[starts-with(@id, 'record_')]")
            for index in range(len(rows)):
                rows = driver.find_elements(
                    By.XPATH, "//tr[starts-with(@id, 'record_')]"
                )
                row = rows[index]
                record_id = row.get_attribute("id")

                try:
                    next_row = row.find_element(By.XPATH, "following-sibling::tr")
                    first_td = next_row.find_element(By.TAG_NAME, "td")
                    link = first_td.find_element(By.TAG_NAME, "a")
                    if link and link.get_attribute("href"):
                        href = link.get_attribute("href")
                        logger.info(f"Accediendo al enlace: {href}")
                        driver.get(href)
                        all_scraper += f"Link: {href}\n"
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                        )

                        page_content = BeautifulSoup(driver.page_source, "html.parser")
                        td_element = page_content.select(
                            'div table:nth-child(1) tr:nth-child(1) td:nth-child(3)[valign="top"]'
                        )
                        if td_element:
                            cleaned_text = " ".join(td_element[0].get_text().split())
                            all_scraper += cleaned_text + "\n"
                        else:
                            logger.warning(
                                f"No se encontró el tercer <td> para el enlace {href}"
                            )
                        all_scraper += "\n\n******************\n\n"
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                        )

                        random_wait()

                except Exception as e:
                    logger.error(
                        f"Error procesando el enlace en la fila con id {record_id}: {str(e)}"
                    )

            driver.get(url)
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "search_string"))
            )

            

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado")


def random_wait(min_wait=2, max_wait=6):
    wait_time = random.uniform(min_wait, max_wait)
    time.sleep(wait_time)
