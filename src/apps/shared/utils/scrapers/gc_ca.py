from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    connect_to_mongo,
    get_logger,
    driver_init,
    process_scraper_data,
    load_keywords
)
from rest_framework.response import Response
from rest_framework import status
from selenium.common.exceptions import TimeoutException

logger = get_logger("scraper")

def scraper_gc_ca(url, sobrenombre):
    driver = driver_init()
    domain = "https://publications.gc.ca"

    try:
        driver.get(url)
        
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)
        
        logger.info(f"Iniciando scraping para URL: {url}")

        collection, fs = connect_to_mongo()
        keywords = load_keywords("plants.txt")

        if not keywords:
            return Response(
                {"status": "error", "message": "El archivo de palabras clave está vacío o no se pudo cargar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_links_found = 0
        total_scraped_successfully = 0
        total_failed_scrapes = 0
        scraped_urls = set()
        failed_urls = set()
        all_scraper = ""

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")

            try:
                driver.get(url)
                driver.execute_script("document.body.style.zoom='100%'")
                WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                time.sleep(5)

                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#ast"))
                )
                search_box.clear()
                search_box.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                search_box.submit()
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error al buscar la palabra clave '{keyword}': {e}")
                continue

            all_links = set()

            while True:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.pagination"))
                    )
                    time.sleep(3)

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    main_container = soup.select_one("main.container")

                    print("🔹 HTML del `main.container` después de esperar:\n", 
                          main_container.prettify() if main_container else "No se encontró `main.container`")

                    result_links = soup.select("div.col-md-8 ol.list-unstyled li a")

                    if not result_links:
                        logger.warning(f"No se encontraron resultados para: {keyword}")
                        break

                    for link in result_links:
                        if "href" in link.attrs:
                            full_url = f"{domain}{link['href']}" if link["href"].startswith("/") else link["href"]
                            all_links.add(full_url)

                    logger.info(f"🔹 Página analizada. Total de links acumulados: {len(all_links)}")

                    next_button = main_container.select_one("a[rel='next']") if main_container else None

                    if not next_button:
                        next_button = soup.select_one("a[rel='next']")

                    if next_button:
                        next_url = next_button["href"]
                        if not next_url.startswith("http"):
                            next_url = f"{domain}{next_url}"

                        logger.info(f"✅ Botón 'Next' encontrado: {next_url}")

                        driver.get(next_url)
                        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                        time.sleep(5)
                    else:
                        logger.info("🚫 No se encontró el botón 'Next'. No hay más páginas disponibles.")
                        break

                except TimeoutException:
                    logger.warning(f"No se encontraron más resultados para '{keyword}'")
                    break

            logger.info(f"Comenzando a procesar {len(all_links)} enlaces almacenados.")
            
            for link in all_links:
                try:
                    driver.get(link)
                    driver.execute_script("document.body.style.zoom='100%'")
                    WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                    time.sleep(5)

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    main_container = soup.select_one("main.container")

                    content_text = main_container.get_text("\n", strip=True) if main_container else soup.get_text("\n", strip=True)

                    if content_text:
                        object_id = fs.put(
                            content_text.encode("utf-8"),
                            source_url=link,
                            scraping_date=datetime.now(),
                            metadata={
                                "Etiquetas": ["planta", "plaga"],
                                "contenido": content_text,
                                "url": url
                            }
                        )
                        total_scraped_successfully += 1
                        scraped_urls.add(link)

                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                        existing_versions = list(fs.find({"source_url": link}).sort("uploadDate", -1))
                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(oldest_version._id)
                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version._id}")
                    else:
                        total_failed_scrapes += 1
                        failed_urls.add(link)

                except Exception as e:
                    logger.error(f"No se pudo extraer contenido de {link}: {e}")
                    total_failed_scrapes += 1
                    failed_urls.add(link)

        all_scraper += f"Total enlaces encontrados: {len(all_links)}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        if driver:
            driver.quit()
            logger.info("Navegador cerrado")
