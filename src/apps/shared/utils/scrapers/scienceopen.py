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
    delete_old_documents,
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
    extract_text_from_pdf
)
from rest_framework.response import Response
from rest_framework import status
from selenium.webdriver.common.keys import Keys

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
                scraping_failed = True
                continue

            content_accumulated = ""
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
                        next_page_button = driver.find_element(By.CSS_SELECTOR, "button.so-b3.so--tall")
                        driver.execute_script("arguments[0].click();", next_page_button)
                        time.sleep(2)
                    except NoSuchElementException:
                        logger.info("No hay más páginas disponibles para esta palabra clave.")
                        break  
                except TimeoutException:
                    logger.warning(f"No se encontraron resultados para '{keyword}' después de esperar.")
                    break
                
                urls_by_keyword[keyword] = fullhrefs
                fullhrefs = []

        for word in urls_by_keyword:
            keyword_folder = generate_directory(word, main_folder)
            keyword_file_path = get_next_versioned_filename(keyword_folder, word)
            print(f"///////////////////Guardando información en el archivo: {keyword_file_path}")
            
            for href in urls_by_keyword[word]:
                if href:
                    driver.get(href)
                    visited_urls.add(href)
                    time.sleep(random.uniform(3, 6))
                    
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    body = soup.select_one("section.so-layout-section div.so-d")
                    body_text = body.get_text(separator=" ", strip=True) if body else "No body found"
                    
                    if body_text:
                        content_accumulated += f"URL:{href} \n\n\n{body_text}" + "-" * 100 + "\n\n"
                        print(f"Página procesada y guardada: {href}")
                        print(f"info guardada: {body_text}")
                    
        if content_accumulated:
            with open(keyword_file_path, "w", encoding="utf-8") as keyword_file:
                keyword_file.write(content_accumulated)
                
            with open(keyword_file_path, "rb") as file_data:
                object_id = fs.put(
                    file_data,
                    filename=os.path.basename(keyword_file_path),
                    metadata={"url": url, "keyword": keyword, "content": content_accumulated, "scraping_date": datetime.now()}
                )
            logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

        return Response({"Mensaje": "Los datos han sido scrapeados correctamente."}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error en el scraping: {str(e)}")
        return Response({"Mensaje": "Ocurrió un error en el scraping."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        driver.quit()
        logger.info("Navegador cerrado")
