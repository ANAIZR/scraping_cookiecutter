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
    process_scraper_data_v2
)
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId

logger = get_logger("scraper")

def scraper_ippc_int(url, sobrenombre):
    driver = initialize_driver()
    total_scraped_links = 0
    scraped_urls = []
    non_scraped_urls = []

    try:
        driver.get(url)
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
        except Exception as e:
            logger.error(f"Error al inicializar el scraper: {str(e)}")

        for keyword in keywords:
            print(f"Buscando con la palabra clave: {keyword}")
            try:

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".form-control.form-control-sm"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                
                logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                continue


            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.ID, "publications"))
                    )
                    logger.info("Resultados encontrados en la página.")
                    
                    try:
                        items = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, "tr.odd, tr.even")
                            )
                        )
                    except Exception as e:
                        logger.warning("No se encontraron elementos en la página.")
                        items = []  # Asegurar que items sea una lista vacía

                    time.sleep(random.uniform(3, 6))
                    if items:
                        logger.info(f"Item encontrados {len(items)} resultados.")
                        for item in items:
                            try:
                                href = item.find_element(By.CSS_SELECTOR, "td > table > tbody > tr > td a").get_attribute("href")
                            except NoSuchElementException:
                                href = None
                                # Opcional: registrar el error
                                logger.info("Elemento no encontrado, continuando...")

                            if href:                                
                                print("href by quma: ", href)
                                driver.get(href)
                                visited_urls.add(href)

                                if href.lower().endswith(".pdf"):
                                    logger.info(f"Extrayendo texto de PDF: {href}")
                                    body_text = extract_text_from_pdf(href)

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

                                    collection.insert_one(
                                        {
                                            "_id": object_id,
                                            "source_url": href,
                                            "scraping_date": datetime.now(),
                                            "Etiquetas": ["planta", "plaga"],
                                            "url": url,
                                        }
                                    )

                                    existing_versions = list(
                                        collection.find({"source_url": href}).sort(
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
                                            f"Se eliminó la versión más antigua con este enlace: '{href}' y object_id: {oldest_version['_id']}"
                                        )
                                else:
                                    non_scraped_urls.append(href)
                                    
                                driver.back()
                                WebDriverWait(driver, 60).until(
                                    EC.presence_of_element_located((By.ID, "publications"))
                                )
                                time.sleep(random.uniform(3, 6))
                            else:
                                logger.info("No se encontró el enlace en el elemento o no existe el elemento.")
                    else:
                        logger.info(f"Item no existen {len(items)} resultados.")
                        driver.get(url)
                        time.sleep(random.uniform(3, 6))

                    try:
                        logger.info("Buscando botón para la siguiente página.")
                        next_page_button = driver.find_element(
                            By.ID,
                            "publications_next",
                        )

                        # Verificar si tiene la clase "disabled"
                        if "disabled" in next_page_button.get_attribute("class"):
                            logger.info(
                                "No hay más páginas disponibles. Finalizando búsqueda para esta palabra clave."
                            )
                            break
                        else:
                            logger.info(
                                f"Yendo a la siguiente página"
                            )
                            next_page_button.click()

                    except NoSuchElementException:
                        logger.info(
                            "No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave."
                        )
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
