from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import random
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status

# Funciones externas
from ..functions import (
    initialize_driver,
    get_logger,
    connect_to_mongo,
    extract_text_from_pdf,
    load_keywords,
    generate_directory,            # IMPORTAMOS LA FUNCIÓN PARA CREAR DIRECTORIOS
    get_next_versioned_filename    # IMPORTAMOS LA FUNCIÓN PARA GENERAR NOMBRES DE ARCHIVO VERSIONADOS
)

def scraper_search_usa_gov(url, sobrenombre):
    logger = get_logger("SEARCH_USA_GOV")
    driver = None
    try:
        logger.info(f"Iniciando scraping para URL: {url}")
        collection, fs = connect_to_mongo("scrapping-can", "collection")
    
        driver = initialize_driver()
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        
        processed_links = set()
        # Diccionario para almacenar el contenido scrapeado por cada palabra clave
        all_scraper = {}
        keywords = load_keywords("plants.txt")
        
        if not keywords:
            logger.error("El archivo de palabras clave está vacío o no se pudo cargar.")
            return Response(
                {
                    "status": "error",
                    "message": "El archivo de palabras clave está vacío o no se pudo cargar."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Crear el directorio principal usando el parámetro 'sobrenombre'
        main_folder = generate_directory(sobrenombre)
        logger.info(f"Directorio principal creado: {main_folder}")
        
        for keyword in keywords:
            logger.info(f"Procesando la palabra clave: {keyword}")
            scraped_content = ""  # Variable donde se acumulará la información de esta palabra clave
            
            # Espera a que el input de búsqueda esté presente
            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "query"))
            )
            search_input.clear()
            search_input.send_keys(keyword)
            search_input.submit()
            time.sleep(random.uniform(3, 6))

            while True:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                result_divs = soup.select("div.content-block-item.result")
                
                if not result_divs:
                    logger.info("No se encontraron resultados en esta página.")
                    break

                for div in result_divs:
                    link = div.find("a", href=True)
                    if link:
                        full_url = link["href"]
                        
                        if full_url.lower().endswith(".pdf"):
                            if full_url not in processed_links:
                                logger.info(f"Extrayendo texto de PDF: {full_url}")
                                pdf_text = extract_text_from_pdf(full_url)
                                scraped_content += f"\n\nURL: {full_url}\n{pdf_text}\n"
                                processed_links.add(full_url)
                            continue
                        elif full_url not in processed_links:
                            logger.info(f"Extrayendo texto de página web: {full_url}")
                            driver.get(full_url)
                            time.sleep(random.uniform(3, 6))
                            soup_page = BeautifulSoup(driver.page_source, "html.parser")
                            text_div = soup_page.find(
                                "div",
                                class_="usa-width-three-fourths usa-layout-docs-main_content"
                            )
                            text_content = (
                                text_div.get_text(strip=True)
                                if text_div
                                else "No se encontró contenido."
                            )
                            scraped_content += f"\n\nURL: {full_url}\n{text_content}\n"
                            processed_links.add(full_url)

                # Si en este caso no se maneja paginación, salimos del while.
                # En otro escenario, aquí podrías agregar lógica para navegar a la siguiente página.
                break  
            
            # Almacenar el contenido scrapeado en el diccionario para este keyword
            all_scraper[keyword] = scraped_content
            
            # Crear un subdirectorio para la palabra clave dentro del directorio principal
            keyword_folder = generate_directory(keyword, main_folder)
            # Generar un nombre de archivo versionado para guardar el contenido
            keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)
            
            # Guardar el contenido en el archivo
            with open(keyword_file_path, "w", encoding="utf-8") as f:
                f.write(scraped_content)
                
            logger.info(f"Datos de la palabra clave '{keyword}' guardados en {keyword_file_path}")
        
        # # Procesar los datos (si es necesario) antes de enviar la respuesta
        # processed_data = process_scraper_data(all_scraper)
        
        response_data = {
            "Tipo": "Web",
            "Url": url,
            "Mensaje": "Los datos han sido scrapeados correctamente.",
            "Data": all_scraper
        }
        return Response(
            {"data": response_data},
            status=status.HTTP_200_OK,
        )
    
    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "La página está tardando demasiado en responder. Verifique si la URL es correcta o intente nuevamente más tarde."
            },
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )
    except ConnectionError:
        logger.error("Error de conexión a la URL.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "No se pudo conectar a la página web."
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "Ocurrió un error al procesar los datos."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        if driver:
            driver.quit()
