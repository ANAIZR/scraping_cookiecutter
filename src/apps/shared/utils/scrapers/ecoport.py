from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidElementStateException
from bs4 import BeautifulSoup
import time
import random
from rest_framework.response import Response
from bson import ObjectId
from rest_framework import status
from datetime import datetime
from ..functions import (
    connect_to_mongo,
    get_logger,
    driver_init,
    load_keywords,
    process_scraper_data
)

logger = get_logger("scraper")

def scraper_ecoport(url, sobrenombre):
    driver = driver_init()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    
    total_urls_found = 0
    total_urls_scraped = 0
    scraped_urls = set()
    failed_urls = set()
    object_ids = []
    all_scraper = ""

    try:
        driver.get(url)
        domain = "http://ecoport.org"
        keywords = load_keywords("plants.txt")
        
        for keyword in keywords:
            try:
                driver.get(url)
                time.sleep(2)
                logger.info(f"Procesando palabra clave: {keyword}")
                
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "td input"))
                )
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "td input"))
                )
                time.sleep(2)
                search_input.clear()
                time.sleep(1)
                search_input.send_keys(keyword)
                
                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input:nth-child(2)"))
                )
                search_button.click()
                time.sleep(random.uniform(3, 6))
                
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                results = soup.select("tr td a")
                
                if not results:
                    logger.info(f"No se encontraron resultados para la palabra clave: {keyword}")
                    continue
                
                for link in results:
                    href = link.get("href")
                    if href:
                        full_href = domain + href if not href.startswith("http") else href
                        if full_href not in scraped_urls and full_href not in failed_urls:
                            scraped_urls.add(full_href)
                            total_urls_found += 1
                            logger.info(f"Procesando URL: {full_href}")
                            
                            try:
                                driver.get(full_href)
                                time.sleep(random.uniform(3, 6))
                                soup = BeautifulSoup(driver.page_source, "html.parser")
                                
                                title = soup.find("u")
                                title_text = title.get_text(strip=True) if title else "Título no encontrado"
                                
                                tables = soup.select("table.ecoportBanner")
                                ecoport_info = tables[1].get_text("\n", strip=True) if len(tables) > 1 else "No se encontró ecoportBanner"
                                
                                section_table = soup.select_one("table.sectionContainer")
                                search_table = soup.select_one("table.searchResultsTable") if not section_table else None
                                section_info = (section_table.get_text("\n", strip=True) if section_table 
                                                else (search_table.get_text("\n", strip=True) if search_table 
                                                      else "No se encontró sección de contenido ni tabla de resultados"))
                                
                                images = []
                                if search_table:
                                    image_tags = search_table.select("img")
                                    for img in image_tags:
                                        img_src = img.get("src")
                                        if img_src:
                                            images.append(domain + img_src if not img_src.startswith("http") else img_src)
                                
                                content_text = (
                                    f"URL: {full_href}\n"
                                    f"Título: {title_text}\n\n"
                                    f"Información:\n{ecoport_info}\n\n"
                                    f"Texto:\n{section_info}\n"
                                )
                                if images:
                                    content_text += "\nImágenes encontradas:\n" + "\n".join(images) + "\n"
                                content_text += "-" * 100 + "\n\n"
                                
                                if content_text:
                                    object_id = fs.put(
                                        content_text.encode("utf-8"),
                                        source_url=full_href,
                                        scraping_date=datetime.now(),
                                        Etiquetas=["planta", "plaga"],
                                        contenido=content_text,
                                        url=url
                                    )
                                    object_ids.append(object_id)
                                    total_urls_scraped += 1
                                    
                                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                    
                                    collection.insert_one({
                                        "_id": object_id,
                                        "source_url": full_href,
                                        "scraping_date": datetime.now(),
                                        "Etiquetas": ["planta", "plaga"],
                                        "url": url,
                                    })
                                    
                                    existing_versions = list(
                                        collection.find({"source_url": full_href}).sort("scraping_date", -1)
                                    )
                                    if len(existing_versions) > 2:
                                        oldest_version = existing_versions[-1]
                                        fs.delete(oldest_version._id)  
                                        collection.delete_one({"_id": ObjectId(oldest_version["_id"])});
                                        logger.info(f"Se eliminó la versión más antigua para {full_href} (object_id: {oldest_version['_id']})")                                    
                                else:
                                    failed_urls.add(full_href)
                            except Exception as e:
                                logger.error(f"No se pudo extraer contenido de {full_href}: {e}")
                                failed_urls.add(full_href)
                driver.back()
                time.sleep(random.uniform(3, 6))
                
            except (TimeoutException, NoSuchElementException, InvalidElementStateException) as e:
                logger.error(f"Error durante la búsqueda para '{keyword}': {e}")
                continue
            except Exception as e:
                logger.error(f"Error inesperado al procesar '{keyword}': {e}")
                failed_urls.add(keyword)
        
        all_scraper += f"Total enlaces encontrados: {total_urls_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_urls_scraped}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {len(failed_urls)}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"
        
        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
        
    except Exception as e:
        logger.error(f"Error en el scraper: {e}")
        return Response(
            {"message": "Ocurrió un error al procesar los datos."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        driver.quit()
