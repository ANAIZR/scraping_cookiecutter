from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
)
from rest_framework.response import Response
from rest_framework import status
import time
import requests

def fetch_content(href, logger):
    try:
        response = requests.get(href)
        logger.info(f"Accediendo al enlace: {href}")
        if response.status_code != 200:
            logger.error(f"Error al acceder al enlace: {href}, Código de estado: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        inner_content = soup.find(id="inner-content")
        if inner_content:
            content_text = inner_content.get_text(strip=True)
            logger.info(f"Contenido obtenido del enlace: {href}, Longitud: {len(content_text)} caracteres")
            return f"URL: {href}\n{content_text}"
        else:
            logger.error(f"No se encontró contenido interno en la página: {href}")
            return None
    except Exception as e:
        logger.error(f"Error al procesar el enlace {href}: {str(e)}")
        return None

def scraper_iucngisd(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()

    try:
        driver = webdriver.Chrome() 
        driver.get(url)
        logger.info(f"Abriendo URL con Selenium: {url}")

        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "go"))
        )
        search_button.click()
        logger.info("Botón de búsqueda clicado con Selenium.")

        time.sleep(5)  

        page_source = driver.page_source
        driver.quit()

        soup = BeautifulSoup(page_source, "html.parser")

        ul_tag = soup.select_one("ul.content.spec")
        if not ul_tag:
            raise Exception("No se encontró el elemento ul con la clase 'content spec'.")

        hrefs = []
        li_tags = ul_tag.find_all("li")
        for li_tag in li_tags:
            a_tag = li_tag.find("a")
            if a_tag and a_tag.get("href"):
                hrefs.append(a_tag["href"])

        logger.info(f"Enlaces extraídos: {len(hrefs)}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda href: fetch_content(href, logger), hrefs))

        for content in results:
            if content:
                all_scraper += content + "\n\n"

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
