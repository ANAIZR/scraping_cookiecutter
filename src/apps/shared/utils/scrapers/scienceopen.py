from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import pickle
import random
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
    process_scraper_data_v2
)
from rest_framework.response import Response
from rest_framework import status
from selenium.webdriver.common.keys import Keys
from bson import ObjectId

def scroll_down(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 4))
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

logger = get_logger("scraper")

def scraper_scienceopen(url, sobrenombre):
    driver = initialize_driver()
    urls_by_keyword = dict()
    total_scraped_links = 0
    scraped_urls = []
    non_scraped_urls = []    

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        object_id = None
        
        try:
            collection, fs = connect_to_mongo()
            main_folder = generate_directory(sobrenombre)
            keywords = load_keywords("plants.txt")
            if not keywords:
                return Response({"status": "error", "message": "El archivo de palabras clave está vacío o no se pudo cargar."}, status=status.HTTP_400_BAD_REQUEST)
            visited_urls = set()
            scraping_failed = False
        except Exception as e:
            logger.error(f"Error al inicializar el scraper: {str(e)}")

        try:
            with open("cookies.pkl", "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
        except FileNotFoundError:
            logger.info("No se encontraron cookies guardadas.")

        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "so-b3") and normalize-space()="Accept all cookies"]'))
            )
            cookie_button.click()
        except Exception:
            logger.info("El botón de 'Aceptar Cookies' no apareció o no fue clicable.")

        for keyword in keywords:
            fullhrefs = []
            print(f"Buscando con la palabra clave: {keyword}")
            
            try:
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".so-text-input"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                search_input.send_keys(Keys.RETURN)
                logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                continue

            page_number = 1
            while True:
                scroll_down(driver)
                print("Buscando resultados en la página.")
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".so-m-t-20"))
                    )
                    logger.info("Resultados encontrados en la página.")
                    
                    items = driver.find_elements(By.CSS_SELECTOR, "h3.so-article-list-item-title a")
                    for link in items:
                        href = link.get_attribute("href")
                        if href:
                            fullhrefs.append(href)
                            logger.info(f"Enlace extraído: {href}")
                
                    try:
                        if page_number <= 2:
                            next_page_button = driver.find_element(By.CSS_SELECTOR, "button.so-b3.so--tall")
                            driver.execute_script("arguments[0].click();", next_page_button)
                            page_number += 1
                            time.sleep(2)
                        else:
                            logger.info(f"Detectada tercera página: Finalizando scraping tras procesar enlaces.")      
                            driver.get(url)
                            time.sleep(random.uniform(3, 6))               
                            break  # Rompe el bucle tras procesar la página 2                            
                    except NoSuchElementException:
                        logger.info("No hay más páginas disponibles para esta palabra clave.")
                        break  
                except TimeoutException:
                    logger.warning(f"No se encontraron resultados para '{keyword}' después de esperar.")
                    break
                
                urls_by_keyword[keyword] = fullhrefs
                fullhrefs = []

        for word in urls_by_keyword:
            for href in urls_by_keyword[word]:
                if href:
                    driver.get(href)
                    visited_urls.add(href)
                    time.sleep(random.uniform(3, 6))
                    
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    body = soup.select_one("section.so-layout-section div.so-d")
                    body_text = body.get_text(separator=" ", strip=True) if body else "No body found"
                    
                    if body_text:
                        object_id = fs.put(
                            body_text.encode("utf-8"),
                            source_url=href,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=body_text,
                            url=url
                        )
                        total_scraped_links += 1
                        scraped_urls.append(href)
                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                        existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(ObjectId(oldest_version._id))
                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version._id}")
                    else:
                        non_scraped_urls.append(href)
                            

        all_scraper = (
            f"Total enlaces scrapeados: {total_scraped_links}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response
    
    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "La página está tardando demasiado en responder. Verifique si la URL es correcta o intente nuevamente más tarde.",
            },
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )
    except ConnectionError:
        logger.error("Error de conexión a la URL.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "No se pudo conectar a la página web.",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
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
        driver.quit()
        logger.info("Navegador cerrado")
