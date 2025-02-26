from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    load_keywords,
    extract_text_from_pdf,
)
import time
import random
from datetime import datetime
from bson import ObjectId
from urllib.parse import urljoin
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

def scraper_repository_cimmy(url, sobrenombre):
    logger = get_logger("REPOSITORY_CIMMY")
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

    try:
        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)

        print(f"✅ Página cargada correctamente.")

        domain = "https://repository.cimmyt.org"
        keywords = load_keywords("prueba.txt")

        for keyword in keywords:
            try:
                search_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-test='search-box']"))
                )
                search_input.clear()
                search_input.send_keys(keyword)

                try:
                    search_button = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "button.btn.btn-primary.search-button"))
                    )
                    print(f"✅ Se encontró el botón de búsqueda con Selenium")
                except TimeoutException:
                    print(f"No se encontró el botón con Selenium después de la espera")
                    continue

                try:
                    search_button.click()
                except:
                    driver.execute_script("arguments[0].click();", search_button)

                time.sleep(random.uniform(3, 6))

                while True:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    results = soup.select("ds-listable-object-component-loader")

                    for result in results:
                        link = result.find("a", href=True)
                        if link and link["href"]:
                            href = urljoin(domain, link["href"])
                            if href not in scraped_urls and href not in failed_urls:
                                scraped_urls.add(href)
                                total_links_found += 1
                            else:
                                failed_urls.add(href)
                                total_failed_scrapes += 1
                                

                    try:
                        next_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[aria-label='Next']"))
                        )

                        if next_button.get_attribute("aria-disabled") == "true":
                            print("🔚 Botón 'Next' deshabilitado. Fin de paginación.")
                            break

                        driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(random.uniform(3, 6))

                    except (TimeoutException, NoSuchElementException):
                        print("No se encontró botón 'Next' o no es clickeable. Fin de paginación.")
                        break

                driver.get(url)
                driver.execute_script("document.body.style.zoom='100%'")
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(5)

            except Exception as e:
                print(f"⚠️ Error durante la búsqueda con palabra clave '{keyword}': {e}")
                continue

        print(f"🔍 Total de URLs únicas para scrapear: {len(scraped_urls)}")  

        for href in scraped_urls.copy():
            try:
                print(f"🔎 Procesando: {href}")  

                if href.endswith(".pdf"):
                    print(f"📄 Extrayendo texto de PDF: {href}")
                    content_text = extract_text_from_pdf(href)
                else:
                    driver.get(href)
                    driver.execute_script("document.body.style.zoom='100%'")
                    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                    time.sleep(5)

                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.col-xs-12.col-md-7"))
                    )
                    time.sleep(random.randint(2, 4))
                    content_text = driver.find_element(By.CSS_SELECTOR, "div.col-xs-12.col-md-7").text.strip()

                if content_text:
                    object_id = fs.put(
                        content_text.encode("utf-8"),
                        source_url=href,
                        scraping_date=datetime.now(),
                        Etiquetas=["planta", "plaga"],
                        contenido=content_text,
                        url=url
                    )

                    object_ids.append(object_id)
                    total_scraped_successfully += 1
                    print(f"✅ Contenido guardado en MongoDB: {href}")  

                    existing_versions = list(
                        fs.find({"source_url": href}).sort("scraping_date", -1)
                    )

                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        fs.delete(ObjectId(oldest_version._id))
                        logger.info(f"Se eliminó la versión más antigua con este enlace: '{href}' y object_id: {oldest_version._id}")
                            
                    logger.info(f"Contenido extraído de {href}.")

                else:
                    print(f"⚠️ El contenido de {href} está vacío.")
                    total_failed_scrapes += 1
                    failed_urls.add(href)

            except Exception as e:
                print(f"❌ No se pudo extraer contenido de {href}: {e}")
                total_failed_scrapes += 1
                failed_urls.add(href)

        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        print(f"⚠️ Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        print("🚪 Navegador cerrado.")