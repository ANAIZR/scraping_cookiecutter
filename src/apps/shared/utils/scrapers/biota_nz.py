from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
    get_random_user_agent,
    process_scraper_data,
)
from rest_framework.response import Response
from rest_framework import status
from selenium.common.exceptions import TimeoutException
from bson import ObjectId

logger = get_logger("scraper")

def scraper_biota_nz(url, sobrenombre):
    driver = initialize_driver()
    base_domain = "https://biotanz.landcareresearch.co.nz"
    total_scraped_links = 0
    scraped_urls = []
    non_scraped_urls = []
    
    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
        collection, fs = connect_to_mongo()
        
        keywords = load_keywords("plants.txt")
        if not keywords:
            return Response(
                {
                    "status": "error",
                    "message": "El archivo de palabras clave está vacío o no se pudo cargar.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Página de BIOTA NZ cargada exitosamente.")

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")
            
            try:
                driver.get(url)
                time.sleep(random.uniform(6, 10))

                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#query"))
                )
                search_box.clear()
                search_box.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                search_box.submit()
            except Exception as e:
                logger.error(f"Error al buscar la palabra clave '{keyword}': {e}")
                continue

            while True:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "list-result"))
                    )
                    logger.info(f"Resultados cargados para: {keyword}")
                    time.sleep(random.uniform(1, 3))
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("div.row-separation.specimen-list-item")

                    if not items:
                        logger.warning(
                            f"No se encontraron resultados para la palabra clave: {keyword}"
                        )
                        break

                    for item in items:
                        link_element = item.select_one("div.col-12 > a[href]")
                        if link_element:
                            href = link_element["href"]
                            full_url = f"{base_domain}{href}"
                            logger.info(f"Procesando enlace: {full_url}")
                            response = requests.get(
                                full_url,
                                headers={"User-Agent": get_random_user_agent()},
                            )

                            if response.status_code == 200:
                                link_soup = BeautifulSoup(
                                    response.content, "html.parser"
                                )
                                body = link_soup.select_one(
                                    "div#detail-page>div.page-content-wrapper>div.details-page-content"
                                )
                                content_text = body.get_text(strip=True) if body else ""
                                
                                if content_text:
                                    object_id = fs.put(
                                        content_text.encode("utf-8"),
                                        source_url=full_url,
                                        scraping_date=datetime.now(),
                                        Etiquetas=["planta", "plaga"],
                                        contenido=content_text,
                                        url=url
                                    )
                                    total_scraped_links += 1
                                    scraped_urls.append(full_url)
                                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                    existing_versions = list(fs.find({"source_url": full_url}).sort("scraping_date", -1))
                                    if len(existing_versions) > 1:
                                        oldest_version = existing_versions[-1]
                                        fs.delete(oldest_version._id)  
                                        logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version.id}")

                                    
                                else:
                                    non_scraped_urls.append(full_url)
                            else:
                                non_scraped_urls.append(full_url)

                    try:
                        next_page = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//a[contains(@class, 'paging-hyperlink') and contains(text(), 'Next')]",
                                )
                            )
                        )
                        driver.execute_script("arguments[0].click();", next_page)
                        time.sleep(random.uniform(6, 10))
                    except Exception:
                        logger.info("No hay más páginas disponibles.")
                        break
                except TimeoutException:
                    logger.warning(
                        f"No se encontraron resultados para '{keyword}' después de esperar."
                    )
                    break

        all_scraper = (
            f"Total enlaces scrapeados: {total_scraped_links}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error al procesar datos del scraper: {str(e)}")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "Ocurrió un error al procesar los datos.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        if driver:
            driver.quit()
            logger.info("Navegador cerrado")
