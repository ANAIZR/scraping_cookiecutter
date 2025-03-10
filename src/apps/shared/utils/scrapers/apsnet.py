from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    connect_to_mongo,
    get_logger,
    driver_init,
    process_scraper_data,
    load_keywords
)
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
import random
import time
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bson import ObjectId
import requests

logger = get_logger("scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
}

def scraper_apsnet(url, sobrenombre):
    driver = None
    try:
        # Verificar el código de respuesta HTTP antes de proceder
        response = requests.get(url, headers=HEADERS)
        if response.status_code in [403, 429, 503]:
            logger.error(f"Acceso denegado o bloqueado con código {response.status_code} en {url}")
            return Response(
                {"error": f"Acceso denegado o bloqueado con código {response.status_code}"},
                status=status.HTTP_403_FORBIDDEN if response.status_code == 403 else status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        driver = driver_init()
        object_id = None

        collection, fs = connect_to_mongo()
        keywords = load_keywords("family.txt")
        scraped_urls = set()
        failed_urls = set()
        total_links_found = 0
        total_scraped_successfully = 0
        total_failed_scrapes = 0
        all_scraper = ""

        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)

        domain = "https://apsjournals.apsnet.org"
        for keyword in keywords:
            try:
                driver.get(url)
                time.sleep(2)

                driver.execute_script("document.body.style.zoom='100%'")
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(5)

                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                html_pretty = soup.prettify().splitlines()[:650]
                for line in html_pretty:
                    print(line)

                search_input_soup = soup.select_one("input#text1")
                if not search_input_soup:
                    logger.warning("❌ No se encontró el input de búsqueda en el DOM con BeautifulSoup.")
                else:
                    logger.info("✅ Input de búsqueda encontrado en el DOM con BeautifulSoup.")

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#text1"))
                )
                search_input.clear()
                search_input.send_keys(keyword)

                search_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button#advanced-search-btn"))
                )
                search_button.click()
                time.sleep(random.uniform(3,6))

                hrefs = []
                while True:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    results_divs = soup.select("ul.rlist.search-result__body li.search__item")
                    for div in results_divs:
                        link = div.find("a", href=True)
                        if link and link["href"]:
                            full_href = domain + link["href"] if not link["href"].startswith("http") else link["href"]
                            if full_href not in scraped_urls and full_href not in failed_urls:
                                hrefs.append(full_href)
                                total_links_found += 1

                    try:
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.pagination__btn--next"))
                        )
                        next_button.click()
                        time.sleep(random.uniform(3,6))
                    except (TimeoutException, NoSuchElementException):
                        break
                
                for idx, link in enumerate(hrefs, start=1):
                    try:
                        print(f"Se está scrapeando ({idx}) y el link es: {link}")
                        driver.get(link)
                        time.sleep(random.uniform(3,6))

                        driver.execute_script("document.body.style.zoom='100%'")
                        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                        time.sleep(5)

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        content_div = soup.select_one("div.article__body")
                        
                        if not content_div:
                            logger.warning(f"No se encontró 'div.article__body' en {link}. Intentando con 'div.abstract'")
                            content_div = soup.select_one("div.abstract")

                        content_text = content_div.get_text(strip=True) if content_div else soup.get_text(strip=True)

                        if content_text and content_text.strip():
                            object_id = fs.put(
                                content_text.encode("utf-8"),
                                source_url=link,
                                scraping_date=datetime.now(),
                                Etiquetas=["planta", "plaga"],
                                contenido=content_text,
                                url=url
                            )
                            total_scraped_successfully += 1
                            scraped_urls.add(link)

                            logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                            existing_versions = list(fs.find({"source_url": link}).sort("scraping_date", -1))
                            if len(existing_versions) > 1:
                                oldest_version = existing_versions[-1]
                                file_id = oldest_version._id  
                                fs.delete(file_id)  
                                logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                        else:
                            total_failed_scrapes += 1
                            failed_urls.add(link)

                    except Exception as e:
                        logger.error(f"No se pudo extraer contenido de {link}: {e}")
                        total_failed_scrapes += 1
                        failed_urls.add(link)

                return process_scraper_data(all_scraper, url, sobrenombre)

            except Exception as e:
                logger.warning(f"Error durante la búsqueda con palabra clave '{keyword}': {e}")
                continue

    except Exception as e:
        logger.error(f"Error durante el scrapeo: {str(e)}")
        return Response(
            {"error": f"Error durante el scrapeo: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        if driver:
            driver.quit()
