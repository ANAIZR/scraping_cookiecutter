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
    process_scraper_data
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
        all_scraper = ""
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
        
        for keyword in keywords:
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
                                all_scraper += f"\n\nURL: {full_url}\n{pdf_text}\n"
                                processed_links.add(full_url)
                            continue
                        else:
                            if full_url not in processed_links:
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
                                all_scraper += f"\n\nURL: {full_url}\n{text_content}\n"
                                processed_links.add(full_url)

                try:
                    next_page_button = driver.find_element(By.CSS_SELECTOR, "a.next_page")
                    if next_page_button.is_displayed() and next_page_button.is_enabled():
                        next_page_link = next_page_button.get_attribute("href")
                        if next_page_link:
                            driver.get(next_page_link)
                            time.sleep(random.uniform(3, 6))
                        else:
                            logger.info("No hay más páginas para navegar.")
                            break
                    else:
                        logger.info("El botón 'next_page' no está visible o no es clickeable.")
                        break
                except NoSuchElementException:
                    logger.info("No se encontró el botón 'next_page'. Fin de la paginación.")
                    break

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
