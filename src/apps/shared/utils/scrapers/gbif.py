from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework import status
from rest_framework.response import Response
from bson import ObjectId

from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    extract_text_from_pdf,
    load_keywords,
)
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def scraper_gbif(url, sobrenombre):
    logger = get_logger("GBIF SCRAPER")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = driver_init()
    collection, fs = connect_to_mongo()
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    all_scraper = ""
    scraped_urls = set()
    failed_urls = set()
    visited_urls = set()
    object_ids = []
    domain = "https://www.gbif.org"

    try:
        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)

        logger.info("✅ Página cargada correctamente.")

        keywords = load_keywords("plants.txt")

        for keyword in keywords:
            print(f"🔍 Buscando palabra clave: {keyword}")
            try:
                search_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#siteSearchInputHome"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                search_input.submit()
                time.sleep(random.uniform(3, 6))

                while True:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")

                    results = soup.select("div.container--narrow div.col-xs-12.m-t-1.ng-scope")

                    print(f"🔍 {len(results)} resultados encontrados para '{keyword}'")

                    for result in results:
                        links = result.select("h3 a")
                        for link in links:
                            href = link.get("href")
                            if href:
                                full_href = urljoin(domain, href)
                                if full_href not in scraped_urls:
                                    scraped_urls.add(full_href)
                                    total_links_found += 1
                                    print(f"✅ URL almacenada: {full_href}")
                                    print(f"🔢 Total links encontrados hasta ahora: {total_links_found}")

                    try:
                        next_page_li = driver.find_element(By.CSS_SELECTOR, "li.pagination-next")
                        next_page_class = next_page_li.get_attribute("class")

                        if "disabled" in next_page_class:
                            print("❌ No hay más páginas en la paginación principal.")
                            break

                        next_page_button = next_page_li.find_element(By.CSS_SELECTOR, "a.ng-binding")
                        print("➡️ Pasando a la siguiente página en la paginación principal...")
                        driver.execute_script("arguments[0].click();", next_page_button)
                        time.sleep(random.uniform(3, 6))

                    except (TimeoutException, NoSuchElementException):
                        print("❌ No se encontró paginación en la página principal.")
                        break

                try:
                    more_info_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "p.clearfix a"))
                    )
                    more_info_href = more_info_button.get_attribute("href")

                    if more_info_href:
                        more_info_url = urljoin(domain, more_info_href)
                        print(f"🔍 Ingresando a página adicional: {more_info_url}")
                        driver.get(more_info_url)
                        time.sleep(random.uniform(3, 6))

                        while True:
                            new_page_source = driver.page_source
                            new_soup = BeautifulSoup(new_page_source, "html.parser")

                            new_results = new_soup.select("div.container--narrow.ng-scope")

                            print(f"🔍 {len(new_results)} secciones encontradas en la página adicional.")

                            for result in new_results:
                                links = result.select("h3 a")
                                for link in links:
                                    new_href = link.get("href")
                                    if new_href:
                                        new_full_href = urljoin(domain, new_href)
                                        if new_full_href not in scraped_urls:
                                            scraped_urls.add(new_full_href)
                                            total_links_found += 1
                                            print(f"✅ URL encontrada desde página adicional: {new_full_href}")
                                            print(f"🔢 Total links encontrados hasta ahora: {total_links_found}")

                            try:
                                next_page_li = driver.find_element(By.CSS_SELECTOR, "li.pagination-next")
                                next_page_class = next_page_li.get_attribute("class")

                                if "disabled" in next_page_class:
                                    print("❌ No hay más páginas en la paginación adicional.")
                                    break

                                next_page_button = next_page_li.find_element(By.CSS_SELECTOR, "a.ng-binding")
                                print("➡️ Pasando a la siguiente página en la paginación adicional...")
                                driver.execute_script("arguments[0].click();", next_page_button)
                                time.sleep(random.uniform(3, 6))

                            except (TimeoutException, NoSuchElementException):
                                print("❌ No se encontró paginación en la página adicional.")
                                break
                        driver.get(url)
                        time.sleep(random.uniform(3, 6))

                except (TimeoutException, NoSuchElementException):
                    print("❌ No se encontró enlace en 'p.clearfix a'. Continuando...")

            except Exception as e:
                logger.warning(f"⚠️ Error durante la búsqueda con palabra clave '{keyword}': {e}")
                continue

        print(f"🔹 Total final de URLs recolectadas antes de scraping: {len(scraped_urls)}")
        total_links_found = len(scraped_urls)

        for scraped_url in scraped_urls:
            try:
                print(f"🔍 Accediendo a: {scraped_url}")
                driver.get(scraped_url)
                time.sleep(random.uniform(3, 6))

                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")

                content_div = (
                    soup.select_one("div.taxonomyBrowser") or 
                    soup.select_one("div.container--narrow") or 
                    soup.select_one("div.col-xs-12.card__content")
                )

                if content_div:
                    content_text = content_div.get_text(strip=True)

                    object_id = fs.put(
                        content_text.encode("utf-8"),
                        source_url=scraped_url,
                        scraping_date=datetime.now(),
                        Etiquetas=["planta", "hongo"],
                        contenido=content_text,
                        url=url
                    )
                    
                    object_ids.append(object_id)
                    total_scraped_successfully += 1
                    print(f"✅ Contenido guardado en MongoDB: {href}")  

                    existing_versions = list(
                        fs.find({"source_url": scraped_url}).sort("scraping_date", -1)
                    )

                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        fs.delete(ObjectId(oldest_version._id))
                        logger.info(f"Se eliminó la versión más antigua con este enlace: '{scraped_url}' y object_id: {oldest_version._id}")

                logger.info(f"✅ Información extraída de {scraped_url}")

            except Exception as e:
                logger.error(f"❌ No se pudo extraer contenido de {scraped_url}: {e}")
                total_failed_scrapes += 1
                failed_urls.add(scraped_url)

        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        return process_scraper_data(all_scraper, url, sobrenombre)

    except Exception as e:
        logger.error(f"⚠️ Error en el scraper: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("🚪 Navegador cerrado.")
