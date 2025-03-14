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
    extract_text_from_pdf,
    process_scraper_data,
    save_to_mongo
)
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId

logger = get_logger("scraper")

def scraper_doaj_org(url, sobrenombre):
    driver = initialize_driver()
    total_scraped_links = 0
    scraped_urls = []
    non_scraped_urls = []

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
            visited_urls = set()
        except Exception as e:
            logger.error(f"Error al inicializar el scraper: {str(e)}")

        for keyword in keywords:
            print(f"Buscando con la palabra clave: {keyword}")
            try:
                # Esperar a que el label esté clickeable
                label = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//label[@for='articles']"))
                )
                # label.click()
                driver.execute_script("arguments[0].click();", label)

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "keywords"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))

                search_input.submit()
                logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                continue

            page_number = 1  # Para controlar el número de página
            
            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.ID, "results"))
                    )
                    logger.info("Resultados encontrados en la página.")

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    try:
                        items = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.card.search-results__record"))
                        )
                    except Exception as e:
                        logger.warning("No se encontraron elementos en la página.")
                        items = []  # Asegurar que items sea una lista vacía

                    time.sleep(random.uniform(3, 6))
                    if items:
                        logger.info(f"Item Encontrados {len(items)} resultados en la página {page_number}.")
                        for item in items:
                            href = item.find_element(By.CSS_SELECTOR, "h3.search-results__heading a").get_attribute("href")

                            if href:
                                driver.get(href)
                                visited_urls.add(href)

                                if href.lower().endswith(".pdf"):
                                    logger.info(f"Extrayendo texto de PDF: {href}")
                                    body_text = extract_text_from_pdf(href)

                                else:
                                    WebDriverWait(driver, 60).until(
                                        EC.presence_of_element_located(
                                            (By.CSS_SELECTOR, "body")
                                        )
                                    )

                                    time.sleep(random.uniform(6, 10))

                                    WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.CLASS_NAME, "article-details__abstract"))
                                    )

                                    soup = BeautifulSoup(driver.page_source, "html.parser")
                                    body = soup.find("p", class_="article-details__abstract")


                                    if body:
                                        body_text = (
                                            body.get_text(separator=" ", strip=True) if body else "No body found"
                                        )
                                        if body_text:
                                            object_id = save_to_mongo("urls_scraper", body_text, href, url)
                                            total_scraped_links += 1
                                            scraped_urls.append(href)
                                            logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                        else:
                                            non_scraped_urls.append(href)
                                                        
                                        driver.back()
                                        WebDriverWait(driver, 60).until(
                                            EC.presence_of_element_located((By.ID, "results"))
                                        )
                                        time.sleep(random.uniform(3, 6))
                            else:
                                logger.info(f"Item no existen {len(items)} resultados.")
                                driver.get(url)
                                time.sleep(random.uniform(3, 6))

                    try:
                        next_page_button = driver.find_element(By.CSS_SELECTOR, "a.doaj-pager-next.doaj-pager-next-bottom-pager")
                        next_page_link = next_page_button.get_attribute("href")
                        
                        if next_page_button and page_number < 2:
                            logger.info(f"Yendo a la siguiente página: {page_number}")
                            driver.get(next_page_link)
                            # next_page_button.click()
                            page_number += 1
                        else:
                            logger.info(f"Detectada tercera página: Finalizando scraping tras procesar enlaces.")      
                            driver.get(url)
                            time.sleep(random.uniform(3, 6))               
                            break  # Rompe el bucle tras procesar la página 2
                    except NoSuchElementException:
                        logger.info("No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave.")
                        driver.get(url)
                        break   
                except TimeoutException:
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

        response = process_scraper_data(all_scraper, url, sobrenombre,collection)
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
