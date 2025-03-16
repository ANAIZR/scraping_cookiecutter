from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import pickle
import random
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    process_scraper_data,
    driver_init,
    get_logger,
    connect_to_mongo,
    load_keywords,
    extract_text_from_pdf,
    save_to_mongo
)
from bson import ObjectId
from rest_framework.response import Response
from rest_framework import status
from ..credentials import login_cabi_scienceconnect

logger = get_logger("scraper")

def scraper_search_usa_gov(url, sobrenombre):
    driver = driver_init()
    object_ids = []
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    all_scraper = ""
    scraped_urls = []
    failed_urls = []
    
    try:
        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)
        time.sleep(random.uniform(6, 10))
        object_id = None
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
            visited_urls = set()
            scraping_failed = False
            base_domain = "https://search.usa.gov"
        except Exception as e:
            logger.error(f"Error al inicializar el scraper: {str(e)}")
            return Response(
                {"status": "error", "message": "Error al inicializar el scraper."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        for keyword in keywords:
            print(f"Buscando con la palabra clave: {keyword}")
            try:
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "query"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                search_input.submit()
                logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                scraping_failed = True
                continue

            content_accumulated = ""
            page_number = 1  

            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.ID, "results"))
                    )
                    logger.info("Resultados encontrados en la página.")

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("div.content-block-item.result")
                    if not items:
                        logger.warning(f"No se encontraron resultados para la palabra clave: {keyword}")
                        break
                    
                    logger.info(f"Encontrados {len(items)} resultados en la página {page_number}.")
                    
                    for item in items:
                        href = item.find("a")["href"]
                        if href and href not in visited_urls:
                            total_links_found += 1  # Incrementa el contador de enlaces encontrados
                            visited_urls.add(href)
                            driver.get(href)
                            driver.execute_script("document.body.style.zoom='100%'")
                            WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
                            time.sleep(5)

                            if href.lower().endswith(".pdf"):
                                logger.info(f"Extrayendo texto de PDF: {href}")
                                body_text = extract_text_from_pdf(href)
                            else:
                                WebDriverWait(driver, 60).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                                )
                                time.sleep(random.uniform(6, 10))
                                soup = BeautifulSoup(driver.page_source, "html.parser")
                                body = soup.find("div", class_=["usa-width-three-fourths", "usa-layout-docs-main_content"])
                                body_text = body.get_text(separator=" ", strip=True) if body else "No body found"
                            
                            if body_text:
                                object_id = save_to_mongo("urls_scraper", body_text, href, url)  # 📌 Guardar en `urls_scraper`
                                total_scraped_successfully += 1
                                scraped_urls.append(href)  
                                logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")
                                
                            else:
                                total_failed_scrapes += 1
                                failed_urls.append(href) 
                                print("No se encontró contenido en la página.")
                            
                            driver.back()
                            WebDriverWait(driver, 60).until(
                                EC.presence_of_element_located((By.ID, "results"))
                            )
                            time.sleep(random.uniform(3, 6))
                    
                    try:
                        next_page_button = driver.find_element(By.CSS_SELECTOR, ".pagination__btn.pagination__btn--next.icon-arrow_r")
                        next_page_link = next_page_button.get_attribute("href")
                        
                        if "page=2" in next_page_link:
                            logger.info(f"Detectada segunda página: {next_page_link}. Finalizando scraping tras procesar enlaces.")
                            driver.get(next_page_link)
                            time.sleep(random.uniform(3, 6))
                            break  
                        else:
                            logger.info(f"Yendo a la siguiente página: {next_page_link}")
                            driver.get(next_page_link)
                            page_number += 1
                    except NoSuchElementException:
                        logger.info("No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave.")
                        driver.get(url)
                        break  
                except TimeoutException:
                    logger.warning(f"No se encontraron resultados para '{keyword}' después de esperar.")
                    break

        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
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
        driver.quit()
        logger.info("Navegador cerrado")
