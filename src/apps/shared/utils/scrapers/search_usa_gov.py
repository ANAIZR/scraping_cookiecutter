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
from ..credentials import login_cabi_scienceconnect
logger = get_logger("scraper")

def scraper_search_usa_gov(url, sobrenombre):
    driver = initialize_driver()
    
    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        object_id = None
        try:

            collection, fs = connect_to_mongo()

            main_folder = generate_directory(sobrenombre)

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
            keyword_folder = generate_directory(keyword, main_folder)
            keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)

            content_accumulated = ""
            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.ID, "results"))
                    )
                    logger.info("Resultados encontrados en la página.")

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("div.content-block-item.result")
                    if not items:
                        logger.warning(
                            f"No se encontraron resultados para la palabra clave: {keyword}"
                        )
                        break
                    logger.info(f"Encontrados {len(items)} resultados.")
                    for item in items:
                        href = item.find("a")["href"]

                        if href:
                            
                            # absolut_href = f"{base_domain}{href}"
                            print("GAAAAA",href)
                            driver.get(href)
                            visited_urls.add(href)

                            # if href.lower().endswith(".pdf"):
                            #     logger.info(f"Extrayendo texto de PDF: {href}")
                            #     body_text = extract_text_from_pdf(href)

                            # else:
                            WebDriverWait(driver, 60).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "body")
                                )
                            )

                            time.sleep(random.uniform(6, 10))
                            soup = BeautifulSoup(driver.page_source, "html.parser")
                            body = soup.find(
                                "div", 
                                class_=["usa-width-three-fourths", "usa-layout-docs-main_content"]
                            )
                            body_text = (
                                body.get_text(strip=True) if body else "No body found"
                            )

                            if body_text:
                                content_accumulated += f"URL:{href} \n\n\n{body_text}"
                                content_accumulated += "-" * 100 + "\n\n"

                                print(f"Página procesada y guardada: {href}")
                            else:
                                print("No se encontró contenido en la página.")
                            driver.back()
                            WebDriverWait(driver, 60).until(
                                EC.presence_of_element_located((By.ID, "results"))
                            )
                            time.sleep(random.uniform(3, 6))

                    try:
                        next_page_button = driver.find_element(
                            By.CSS_SELECTOR,
                            ".pagination__btn.pagination__btn--next.icon-arrow_r",
                        )
                        next_page_link = next_page_button.get_attribute("href")

                        if next_page_link:
                            logger.info(
                                f"Yendo a la siguiente página: {next_page_link}"
                            )
                            driver.get(next_page_link)
                        else:
                            logger.info(
                                "No hay más páginas disponibles. Finalizando búsqueda para esta palabra clave."
                            )
                            break
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

                if len(existing_versions) > 2:
                    oldest_version = existing_versions[-1]  
                    fs.delete(oldest_version["_id"])  
                    collection.delete_one({"_id": oldest_version["_id"]}) 
                    logger.info(
                        f"Se eliminó la versión más antigua de '{keyword}' con URL '{url}' y object_id: {oldest_version['_id']}"
                    )


        if scraping_failed:
            return Response(
                {
                    "message": "Error durante el scraping. Algunas URLs fallaron.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
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
        driver.quit()
        logger.info("Navegador cerrado")
