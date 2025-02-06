from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def scraper_ippc(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""

    try:
        driver.get(url)
        logger.info("Ingresando a la URL principal")
        try:
            select_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "publications_length"))
            )
            select = Select(select_element)

            options = select.options
            if options:
                last_value = options[-1].get_attribute("value") 
                select.select_by_value(last_value)  
            

            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#publications tr"))
            )

            print("Datos cargados correctamente en la tabla.")

        except TimeoutException:
            logger.error("Error: El elemento no se cargó en el tiempo esperado.")

        except NoSuchElementException:
            logger.error("Error: No se encontró el elemento <select>.")

        except Exception as e:
            logger.error(f"Error inesperado: {e}")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("#publications tr")
        if rows:
            for row_index, row in enumerate(rows, start=1):

                tds = row.find_all("td")
                for td in tds:
                    link = td.find("a", href=True)
                    if link:
                        href = link["href"]

                        if href.startswith("/"):
                            href = f"https://www.ippc.int{href}"

                        driver.get(href)
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                        )

                        page_soup = BeautifulSoup(driver.page_source, "html.parser")
                        page_title = page_soup.select_one("#divmainbox > h1")
                        page_content = page_soup.select_one("dl.dl-horizontal")

                        if page_title:
                            all_scraper += page_title.get_text(strip=True) + "\n"
                        if page_content:
                            all_scraper += page_content.get_text(strip=True) + "\n\n"

                        driver.back()
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.container>div.row")
                            )
                        )

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response(
            {"error": "Ocurrió un error durante el scraping."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
