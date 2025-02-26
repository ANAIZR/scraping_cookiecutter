import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    extract_text_from_pdf,
    driver_init,
)
from datetime import datetime
from bson import ObjectId
from urllib.parse import urljoin
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def scraper_ipm_illinois(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    domain = "https://ipm.illinois.edu/diseases"

    all_scraper = ""
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    scraped_urls = set()
    failed_urls = set()
    object_ids = []

    collection, fs = connect_to_mongo()
    driver = driver_init()

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")

        second_tbody = driver.find_element(By.CSS_SELECTOR, "table:nth-of-type(3) tbody")
        logger.info(f"📄 Segundo tbody encontrado: {second_tbody}")

        paragraphs = second_tbody.find_elements(By.CSS_SELECTOR, "table p")

        logger.info(f"🔍 Total de <p> encontrados dentro del tbody: {len(paragraphs)}")

        collected_links = []  # Para almacenar las URLs recolectadas

        for p in paragraphs:
            try:
                a_tag = p.find_element(By.TAG_NAME, "a") if p.find_elements(By.TAG_NAME, "a") else None
                if a_tag:
                    href = a_tag.get_attribute("href")
                    if not href.startswith("http"):
                        href = urljoin(domain, href)

                    collected_links.append(href)
                    total_links_found += 1
            except Exception as e:
                logger.error(f"⚠️ Error obteniendo <a> dentro de <p>: {e}")

        logger.info(f"Enlaces recolectados ({len(collected_links)}): {collected_links}")

        if not collected_links:
            logger.error("⚠️ No se encontraron enlaces dentro del segundo tbody.")
            return Response({"error": "No se encontraron enlaces dentro del segundo tbody."}, status=status.HTTP_404_NOT_FOUND)

        for href in collected_links:
            try:
                logger.info(f"Scrapeando URL: {href}")

                content_text = None

                if href.endswith(".pdf"):
                    logger.info(f"***Extrayendo texto de PDF: {href}")
                    content_text = extract_text_from_pdf(href)
                else:
                    driver.get(href)
                    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    content_text = page_soup.body.text.strip()

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
                    scraped_urls.add(href) 
                    total_scraped_successfully += 1

                    existing_versions = list(
                        fs.find({"source_url": href}).sort("scraping_date", -1)
                    )

                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        fs.delete(ObjectId(oldest_version["_id"]))

                        logger.info(f"Se eliminó la versión más antigua: {oldest_version['_id']}")

                    logger.info(f"✅ Enlace procesado con éxito: {href}")

                else:
                    raise ValueError("No se pudo extraer contenido")

            except Exception as e:
                logger.error(f"❌ Error al procesar {href}: {e}")

                if href not in scraped_urls:
                    failed_urls.add(href)
                    total_failed_scrapes += 1

        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("✅ Navegador cerrado.")