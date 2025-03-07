from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    initialize_driver,
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

def scraper_researchgate(url, sobrenombre):
    logger = get_logger("IPPC INT")
    logger.info(f"Iniciando scraping para URL: {url}")
    
    driver = initialize_driver()
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
        time.sleep(5)  # Esperar por elementos dinámicos
        
        logger.info("Página cargada correctamente.")

        # Extraer enlaces de la página
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        results_divs = soup.select("div.research-detail-header-cta__buttons a")
        
        logger.info(f"Encontrados {len(results_divs)} enlaces en la página.")

        for link in results_divs:
            href = link.get("href")  # Verificar si el enlace tiene atributo href
            if href:
                full_url = urljoin(url, href)  # Convertir en URL absoluta
                if full_url not in visited_urls:
                    visited_urls.add(full_url)
                    scraped_urls.add(full_url)
                    total_links_found += 1
                    logger.info(f"✅ Enlace agregado: {full_url}")

        # Procesar cada enlace
        for href in list(scraped_urls):  # Copia la lista para evitar modificación durante iteración
            try:
                content_text = None
                if href.endswith(".pdf"):
                    logger.info(f"*** Extrayendo texto de {href}")
                    content_text = extract_text_from_pdf(href)
                
                if content_text:  # Solo almacenar si se extrajo contenido
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
                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                    # Limpiar versiones antiguas en MongoDB
                    existing_versions = list(
                        fs.find({"source_url": href}).sort("scraping_date", -1)
                    )

                    if len(existing_versions) > 2:
                        oldest_version = existing_versions[-1]
                        fs.delete(ObjectId(oldest_version["_id"]))
                        logger.info(f"Se eliminó la versión más antigua de {href} con object_id: {oldest_version['_id']}")

                else:
                    raise ValueError("No se pudo extraer contenido del PDF.")

            except Exception as e:
                logger.error(f"❌ Error al procesar {href}: {str(e)}")
                total_failed_scrapes += 1
                failed_urls.add(href)
                scraped_urls.discard(href)  # Evita que una URL fallida cuente como scrapeada

        # Resumen de scraping
        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"⚠️ Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado.")
