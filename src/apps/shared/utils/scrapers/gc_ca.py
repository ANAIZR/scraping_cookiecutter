from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import random
import requests
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
    get_random_user_agent,
)
from rest_framework.response import Response
from rest_framework import status
from selenium.common.exceptions import TimeoutException

logger = get_logger("scraper")

def scraper_gc_ca(url, sobrenombre):
    driver = initialize_driver()
    domain = "https://publications.gc.ca"
    
    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
        
        collection, fs = connect_to_mongo()
        main_folder = generate_directory(sobrenombre)
        keywords = load_keywords("plants.txt")
        
        if not keywords:
            return Response(
                {"status": "error", "message": "El archivo de palabras clave está vacío o no se pudo cargar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")
            
            try:
                driver.get(url)
                time.sleep(random.uniform(6, 10))
                
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input#ast"))
                )
                search_box.clear()
                search_box.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                search_box.submit()
            except Exception as e:
                logger.error(f"Error al buscar la palabra clave '{keyword}': {e}")
                continue
            
            keyword_folder = generate_directory(keyword, main_folder)
            keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)
            content_accumulated = ""
            
            while True:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.col-md-8 ol.list-unstyled li a"))
                    )
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    result_links = soup.select("div.col-md-8 ol.list-unstyled li a")
                    
                    if not result_links:
                        logger.warning(f"No se encontraron resultados para: {keyword}")
                        break
                    
                    links = list(set(
                        [f"{domain}{link['href']}" if link["href"].startswith("/") else link["href"] 
                        for link in result_links if "href" in link.attrs]
                    ))
                    
                    for link in links:
                        headers = {"User-Agent": get_random_user_agent()}
                        max_retries = 3
                        body_text = ""

                        for attempt in range(max_retries):
                            try:
                                response = requests.get(link, headers=headers, timeout=30)
                                response.raise_for_status()
                                soup = BeautifulSoup(response.text, "html.parser")
                                main_container = soup.select_one("main.container")
                                
                                if main_container:
                                    for tbody in main_container.select("tbody"):
                                        for tr in tbody.find_all("tr"):
                                            tr.insert_after("\n")
                                    
                                    body_text = main_container.get_text("\n", strip=True)
                                break
                            except requests.exceptions.RequestException as e:
                                logger.warning(f"Intento {attempt+1} fallido para {link}: {e}")
                                time.sleep(5)
                        else:
                            logger.error(f"No se pudo extraer contenido después de {max_retries} intentos para {link}")
                        
                        if not body_text:
                            try:
                                driver.get(link)
                                time.sleep(random.uniform(6, 10))
                                soup = BeautifulSoup(driver.page_source, "html.parser")
                                main_container = soup.select_one("main.container")
                                
                                if main_container:
                                    for tbody in main_container.select("tbody"):
                                        for tr in tbody.find_all("tr"):
                                            tr.insert_after("\n")
                                    
                                    body_text = main_container.get_text("\n", strip=True)
                            except Exception as e:
                                logger.warning(f"No se pudo extraer contenido de {link} con Selenium: {e}")

                        if body_text:
                            content_accumulated += f"URL: {link}\nTexto: {body_text}\n\n" + "-" * 100 + "\n\n"
                    
                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, "a[rel='next']")
                        if next_button:
                            next_button.click()
                            time.sleep(random.uniform(6, 10))
                        else:
                            break
                    except Exception:
                        logger.info("No hay más páginas disponibles.")
                        break
                except TimeoutException:
                    logger.warning(f"No se encontraron más resultados para '{keyword}'")
                    break
            
            if content_accumulated:
                with open(keyword_file_path, "w", encoding="utf-8") as keyword_file:
                    keyword_file.write(content_accumulated)
                
                with open(keyword_file_path, "rb") as file_data:
                    object_id = fs.put(
                        file_data,
                        filename=os.path.basename(keyword_file_path),
                        metadata={
                            "url": url,
                            "keyword": keyword,
                            "content": content_accumulated,
                            "scraping_date": datetime.now(),
                            "Etiquetas": ["planta", "plaga"],
                        },
                    )
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                existing_versions = list(
                    collection.find({
                        "metadata.keyword": keyword,
                        "metadata.url": url  
                    }).sort("metadata.scraping_date", -1)
                )
                logger.info(f"Versiones encontradas para '{keyword}': {existing_versions}")

                if len(existing_versions) > 2:
                    oldest_version = existing_versions[-1]  
                    fs.delete(oldest_version["_id"])  
                    collection.delete_one({"_id": oldest_version["_id"]}) 
                    logger.info(
                        f"Se eliminó la versión más antigua de '{keyword}' con URL '{url}' y object_id: {oldest_version['_id']}"
                    )

        data = {
            "Objeto": object_id,
            "Tipo": "Web",
            "Url": url,
            "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["planta", "plaga"],
        }
        response_data = {
            "Tipo": "Web",
            "Url": url,
            "Fecha_scraper": data["Fecha_scraper"],
            "Etiquetas": data["Etiquetas"],
            "Mensaje": "Los datos han sido scrapeados correctamente.",
        }
        logger.info(f"DEBUG - Tipo de respuesta de save_scraper_data_pdf: {type(response_data)}")

        collection.insert_one(data)
        delete_old_documents(url, collection, fs)

        return Response(
            {
                "data": response_data,
            },
            status=status.HTTP_200_OK,
        )

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
        if driver:
            driver.quit()
            logger.info("Navegador cerrado")
