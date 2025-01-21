from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import pickle
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
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = get_logger("scraper")


def scraper_biota_nz(url, sobrenombre):
    content_found = False
    object_id = None
    driver = initialize_driver()
    base_domain = "https://biotanz.landcareresearch.co.nz"
    all_links = []

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
        collection, fs = connect_to_mongo("scrapping-can", "collection")
        main_folder = generate_directory(url)

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

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")

            try:
                # Volver al URL inicial antes de cada búsqueda
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
                            all_links.append(full_url)
                            logger.info(f"Enlace recolectado: {full_url}")

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

        driver.quit()

        def process_link(link):
            nonlocal object_id
            headers = {"User-Agent": get_random_user_agent()}
            try:
                response = requests.get(link, timeout=10, headers=headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "html.parser")
                    body = soup.select_one(
                        "div#detail-page>div.page-content-wrapper>div.details-page-content"
                    )
                    body_text = body.get_text(strip=True) if body else None

                    if body_text:
                        keyword_folder = generate_directory(link, main_folder)
                        file_path = get_next_versioned_filename(
                            keyword_folder, sobrenombre
                        )
                        contenido = f"URL: {link}\n\n{body_text}"

                        with open(file_path, "w", encoding="utf-8") as file:
                            file.write(contenido)

                        with open(file_path, "rb") as file_data:
                            object_id = fs.put(
                                file_data,
                                filename=os.path.basename(file_path),
                            )

                        logger.info(f"Contenido guardado para {link}")
                        return True
                    else:
                        logger.warning(f"No se encontró contenido en {link}")
                        return False
                else:
                    logger.warning(
                        f"Solicitud fallida para {link} con código {response.status_code}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error al procesar el enlace {link}: {e}")
                return False

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(process_link, link): link for link in all_links}
            for future in as_completed(futures):
                link = futures[future]
                try:
                    if future.result():
                        content_found = True
                except Exception as e:
                    logger.error(f"Error procesando el enlace {link}: {e}")

        if content_found:
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
                    "status": "success",
                    "message": "Los datos han sido scrapeados correctamente.",
                    "data": response_data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "status": "success",
                    "message": "El scraping se completó, pero no se encontró contenido para guardar.",
                },
                status=status.HTTP_200_OK,
            )

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response(
            {"status": "error", "message": f"Error durante el scraping: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        if driver:
            driver.quit()
