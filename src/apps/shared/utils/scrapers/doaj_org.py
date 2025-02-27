from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
    extract_text_from_pdf,
    process_scraper_data_v2
)
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId

logger = get_logger("scraper")

def scraper_doaj_org(url, sobrenombre):
    driver = initialize_driver()
    total_scraped_links = 0
    scraped_urls = set()
    non_scraped_urls = set()
    visited_urls = set()

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))

        try:
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
        except Exception as e:
            logger.error(f"Error al inicializar el scraper: {str(e)}")

        for keyword in keywords:
            logger.info(f"🔍 Buscando con la palabra clave: {keyword}")
            try:
                label = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//label[@for='articles']"))
                )
                driver.execute_script("arguments[0].click();", label)

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "keywords"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))

                search_input.submit()
            except Exception as e:
                logger.info(f"❌ Error al realizar la búsqueda: {e}")
                continue

            page_number = 1  

            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.ID, "results"))
                    )
                    logger.info(f"✅ Resultados encontrados en la página {page_number}.")

                    try:
                        items = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.card.search-results__record"))
                        )
                    except Exception:
                        logger.warning("⚠️ No se encontraron elementos en la página.")
                        items = []

                    time.sleep(random.uniform(3, 6))
                    if items:
                        logger.info(f"📌 Encontrados {len(items)} resultados en la página {page_number}.")

                        for index in range(len(items)):  
                            try:
                                items = WebDriverWait(driver, 10).until(
                                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.card.search-results__record"))
                                )
                                item = items[index]  
                                href = item.find_element(By.CSS_SELECTOR, "h3.search-results__heading a").get_attribute("href")

                                if href and href not in visited_urls:  
                                    visited_urls.add(href)  
                                    driver.get(href)

                                    if href.lower().endswith(".pdf"):
                                        logger.info(f"📄 Extrayendo texto de PDF: {href}")
                                        body_text = extract_text_from_pdf(href)

                                    else:
                                        WebDriverWait(driver, 60).until(
                                            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                                        )
                                        time.sleep(random.uniform(6, 10))

                                        try:
                                            WebDriverWait(driver, 10).until(
                                                EC.presence_of_element_located((By.CLASS_NAME, "article-details__abstract"))
                                            )
                                            soup = BeautifulSoup(driver.page_source, "html.parser")
                                            body = soup.find("p", class_="article-details__abstract")
                                            body_text = body.get_text(separator=" ", strip=True) if body else "No tiene información disponible"
                                        except Exception:
                                            body_text = "No tiene información disponible"

                                        if body_text:
                                            try:
                                                object_id = fs.put(
                                                    body_text.encode("utf-8"),
                                                    source_url=href,
                                                    scraping_date=datetime.now(),
                                                    Etiquetas=["planta", "plaga"],
                                                    contenido=body_text,
                                                    url=url
                                                )
                                                total_scraped_links += 1
                                                scraped_urls.add(href) 
                                                logger.info(f"📂 Archivo almacenado en MongoDB con object_id: {object_id}")
                                                
                                                existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                                                if len(existing_versions) > 1:
                                                    oldest_version = existing_versions[-1]
                                                    file_id = oldest_version._id  
                                                    fs.delete(file_id)  
                                                    logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                                            except Exception as e:
                                                logger.error(f"❌ Error al guardar en MongoDB: {e}")
                                                non_scraped_urls.add(href)
                                        else:
                                            non_scraped_urls.add(href)

                                        driver.back()
                                        WebDriverWait(driver, 60).until(
                                            EC.presence_of_element_located((By.ID, "results"))
                                        )
                                        time.sleep(random.uniform(3, 6))
                            except StaleElementReferenceException:
                                logger.warning("⚠️ Stale Element encontrado. Intentando de nuevo...")
                                time.sleep(2)
                                continue  

                    try:
                        next_page_button = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "a.doaj-pager-next.doaj-pager-next-bottom-pager"))
                        )
                        next_page_link = next_page_button.get_attribute("href")

                        if next_page_link and next_page_link not in visited_urls:
                            visited_urls.add(next_page_link)
                            logger.info(f"➡️ Yendo a la siguiente página: {page_number + 1}")
                            driver.get(next_page_link)

                            # 🔹 **Esperar a que los nuevos resultados carguen**
                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.ID, "results"))
                            )

                            page_number += 1
                            time.sleep(random.uniform(3, 6))  
                        else:
                            logger.info(f"🚀 No hay más páginas para procesar. Finalizando scraping.")
                            break  
                    except (NoSuchElementException, TimeoutException):
                        logger.info("🔚 No se encontró el botón para la siguiente página. Finalizando búsqueda.")
                        break   
                except TimeoutException:
                    logger.warning(f"⏳ No se encontraron resultados para '{keyword}' después de esperar.")
                    break

        non_scraped_urls -= scraped_urls  

        all_scraper = (
            f"Total enlaces scrapeados: {total_scraped_links}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response

    finally:
        driver.quit()
        logger.info("🚪 Navegador cerrado")
