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
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
    process_scraper_data_v2
)
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId

def scraper_sciencedirect(url, sobrenombre):
    
    driver = initialize_driver()
    logger = get_logger("scraper")
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

        for keyword in keywords:
            logger.info(f"Buscando con la palabra clave: {keyword}")
            try:
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "qs"))
                )
                search_input.clear()
                search_input.send_keys(keyword)

                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button"))
                )
                search_button.click()
                time.sleep(random.uniform(3, 6))
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                continue

            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.ID, "srp-results-list"))
                    )
                    results_list = driver.find_elements(By.CSS_SELECTOR, "#srp-results-list a")

                    urls = [
                        result.get_attribute("href")
                        for result in results_list
                        if result.get_attribute("href") 
                            and result.get_attribute("href").lower().startswith("https://www.sciencedirect.com/science/article/pii")
                            and not result.get_attribute("href").lower().endswith(".pdf")
                    ]
                    logger.info(f"{len(urls)} resultados filtrados para procesar.")

                    for full_url in urls:

                        driver.get(full_url)
                        WebDriverWait(driver, 60).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                        )
                        time.sleep(random.uniform(6, 10))

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        title_text = soup.select_one("#screen-reader-main-title").get_text(strip=True) if soup.select_one("#screen-reader-main-title") else ""
                        abstract_text = soup.select_one("#abstracts").get_text(strip=True) if soup.select_one("#abstracts") else "No abstract found"
                        introductin_text = soup.select_one("#preview-section-introduction").get_text(strip=True) if soup.select_one("#preview-section-introduction") else "No preview-section-introduction found"
                        snippets_text = soup.select_one("#preview-section-snippets").get_text(strip=True) if soup.select_one("#preview-section-snippets") else "No abstract found"

                        # print('variables booleanas de title_text', title_text)
                        # print('variables booleanas de abstract_text', abstract_text)
                        # print('variables booleanas de introductin_text', introductin_text)
                        # print('variables booleanas de snippets_text', snippets_text)
                        contenido = ""
                        if (title_text or abstract_text or introductin_text or snippets_text):
                            if title_text: contenido += f"{title_text}\n\n\n"
                            if abstract_text: contenido += f"{abstract_text}\n\n\n"
                            if introductin_text: contenido += f"{introductin_text}\n\n\n"
                            if snippets_text: contenido += f"{snippets_text}\n\n\n"

                            if contenido:
                                object_id = fs.put(
                                    contenido.encode("utf-8"),
                                    source_url=full_url,
                                    scraping_date=datetime.now(),
                                    Etiquetas=["planta", "plaga"],
                                    contenido=contenido,
                                    url=url
                                )
                                total_scraped_links += 1
                                scraped_urls.append(full_url)
                                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                                collection.insert_one(
                                    {
                                        "_id": object_id,
                                        "source_url": full_url,
                                        "scraping_date": datetime.now(),
                                        "Etiquetas": ["planta", "plaga"],
                                        "url": url,
                                    }
                                )

                                existing_versions = list(
                                    collection.find({"source_url": full_url}).sort(
                                        "scraping_date", -1
                                    )
                                )

                                if len(existing_versions) > 1:
                                    oldest_version = existing_versions[-1]
                                    fs.delete(ObjectId(oldest_version["_id"]))
                                    collection.delete_one(
                                        {"_id": ObjectId(oldest_version["_id"])}
                                    )
                                    logger.info(
                                        f"Se eliminó la versión más antigua con este enlace: '{full_url}' y object_id: {oldest_version['_id']}"
                                    )
                            else:
                                non_scraped_urls.append(full_url)

                            logger.info(f"Página procesada y guardada: {full_url}")
                        else:
                            logger.info("No se encontró contenido en la página.")
                        driver.back()
                        time.sleep(random.uniform(3, 6))

                    try:
                        next_page_button = driver.find_element(By.CSS_SELECTOR, "a.anchor[data-aa-name='srp-next-page']")
                        
                        if next_page_button:
                            next_page_link = next_page_button.get_attribute("href")
                            logger.info(f"Yendo a la siguiente página: {next_page_link}")
                            driver.get(next_page_link)
                            time.sleep(random.uniform(3, 6))
                        else:
                            logger.info("No hay más páginas disponibles. Finalizando búsqueda para esta palabra clave.")
                            break
                    except NoSuchElementException:
                        logger.info("No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave.")
                        driver.get(url)
                        break
                except Exception as e:
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

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response
    
    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response(
            {"status": "error", "message": f"Error durante el scraping: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        driver.quit()