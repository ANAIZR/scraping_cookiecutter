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
from bson import ObjectId

logger = get_logger("scraper")


def scraper_biota_nz(url, sobrenombre):
    driver = initialize_driver()
    base_domain = "https://biotanz.landcareresearch.co.nz"

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
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

        logger.info("Página de BIOTA NZ cargada exitosamente.")

        scraping_exitoso = False
        object_ids = []

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")

            try:
                driver.get(url)
                time.sleep(random.uniform(6, 10))

                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#query"))
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

            while True:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "list-result"))
                    )
                    logger.info(f"Resultados cargados para: {keyword}")
                    time.sleep(random.uniform(1, 3))
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("div.row-separation.specimen-list-item")

                    if not items:
                        logger.warning(
                            f"No se encontraron resultados para la palabra clave: {keyword}"
                        )
                        break

                    for item in items:
                        link_element = item.select_one("div.col-12 > a[href]")
                        if link_element:
                            href = link_element["href"]
                            full_url = f"{base_domain}{href}"
                            logger.info(f"Procesando enlace: {full_url}")
                            response = requests.get(
                                full_url,
                                headers={"User-Agent": get_random_user_agent()},
                                timeout=10  
                            )

                            if response.status_code == 200:
                                link_soup = BeautifulSoup(
                                    response.content, "html.parser"
                                )
                                body = link_soup.select_one(
                                    "div#detail-page>div.page-content-wrapper>div.details-page-content"
                                )
                                body_text = body.get_text(strip=True) if body else ""
                                content_accumulated = f"Texto: {body_text}"

                                print(f"Página procesada y guardada: {full_url}")
                                if content_accumulated:
                                    
                                    object_id = fs.put(
                                            content_accumulated.encode("utf-8"),
                                            metadata={
                                                "url": full_url,
                                                "scraping_date": datetime.now(),
                                                "Etiquetas": ["planta", "plaga"],
                                                "contenido": content_accumulated,
                                            },
                                        )
                                    object_ids.append(object_id)
                                    logger.info(
                                        f"Archivo almacenado en MongoDB con object_id: {object_id}"
                                    )

                                    collection.insert_one(
                                        {
                                            "_id": object_id,
                                            "url": full_url,
                                            "scraping_date": datetime.now(),
                                            "Etiquetas": ["planta", "plaga"],
                                        }
                                    )

                                    existing_versions = list(
                                        collection.find({"url": full_url}).sort(
                                            "scraping_date", -1
                                        )
                                    )

                                    if len(existing_versions) > 2:
                                        oldest_version = existing_versions[-1]
                                        fs.delete(ObjectId(oldest_version["_id"]))
                                        collection.delete_one(
                                            {"_id": ObjectId(oldest_version["_id"])}
                                        )
                                        logger.info(
                                            f"Se eliminó la versión más antigua de '{keyword}' con URL '{full_url}' y object_id: {oldest_version['_id']}"
                                        )
                                    scraping_exitoso = True

                    try:
                        next_page = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//a[contains(@class, 'paging-hyperlink') and contains(text(), 'Next')]",
                                )
                            )
                        )
                        driver.execute_script("arguments[0].click();", next_page)
                        time.sleep(random.uniform(6, 10))
                    except Exception:
                        logger.info("No hay más páginas disponibles.")
                        break
                except TimeoutException:
                    logger.warning(
                        f"No se encontraron resultados para '{keyword}' después de esperar."
                    )
                    break

        if scraping_exitoso:

            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Etiquetas": ["planta", "plaga"],
                    "Mensaje": "Los datos han sido scrapeados correctamente.",
                    "Object_Ids": [
                        str(obj_id) for obj_id in object_ids
                    ],  # Convertimos ObjectId a string
                },
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos relevantes en el scraping.",
                },
                status=status.HTTP_204_NO_CONTENT,
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

    except requests.ConnectionError:
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
