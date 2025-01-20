from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import pickle
import random
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
)
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("scraper")


def scraper_biota_nz(url, sobrenombre):
    driver = initialize_driver()
    base_domain = "https://biotanz.landcareresearch.co.nz"

    try:
        driver.get(url)

        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
        collection, fs = connect_to_mongo("scrapping-can", "collection")
        main_folder = generate_directory(url)

        keywords = load_keywords("plants.txt")
        visited_urls = set()
        scraping_failed = False
        logger.info("Página de BIOTA NZ cargada exitosamente.")

        # Localizar la barra de búsqueda en Google Académico

        for keyword in keywords:
            print(f"Buscando la palabra clave: {keyword}")
            keyword_folder = generate_directory(keyword, main_folder)
            try:

                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#query"))
                )
                logger.info("Barra de búsqueda localizada.")
                logger.info(f"Buscando la palabra clave: {keyword}")

                # Introducir un tiempo de espera aleatorio antes de interactuar con el buscador
                time.sleep(random.uniform(6, 10))

                # Ingresar la palabra clave y presionar Enter
                search_box.clear()
                search_box.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                search_box.submit()
            except Exception as e:
                logger.error(f"Error al buscar la palabra clave: {str(e)}")
                scraping_failed = True
                continue
            while True:
                try:
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.ID, "list-result"))
                    )
                    logger.info(f"Resultados cargados para: {keyword}")
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("div.row-separation.specimen-list-item")

                    print(f"Encontrados {len(items)} resultados.")

                    for item in items:
                        try:
                            link_element = item.select_one("div.col-12 > a")
                            if link_element:
                                href_element = item.select_one("div.col-12 > a[href]")
                                href = href_element["href"]
                                print(f"Enlace encontrado: {href}")
                                full_url = f"{base_domain}{href}"

                                driver.get(full_url)
                                visited_urls.add(full_url)
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "div.page-content-wrapper")
                                    )
                                )
                                time.sleep(random.uniform(6, 10))
                                soup = BeautifulSoup(driver.page_source, "html.parser")
                                body = soup.select_one("div.page-content-wrapper")
                                body_text = (
                                    body.get_text(strip=True)
                                    if body
                                    else "No body found"
                                )
                                if body_text:
                                    contenido = f"{body_text}\n\n\n"
                                    link_folder = generate_directory(
                                        href, keyword_folder
                                    )
                                    file_path = get_next_versioned_filename(
                                        link_folder, keyword
                                    )
                                    with open(file_path, "w", encoding="utf-8") as file:
                                        file.write(contenido)

                                    with open(file_path, "rb") as file_data:
                                        object_id = fs.put(
                                            file_data,
                                            filename=os.path.basename(file_path),
                                        )

                                    print(f"Página procesada y guardada: {href}")
                                else:
                                    print("No se encontró contenido en la página.")
                                driver.back()
                                WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (By.ID, "list-result")
                                    )
                                )
                                time.sleep(random.uniform(3, 6))

                        except Exception:
                            logger.error("No tiene url")
                            continue
                    print("Fin de la página.")
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
                    except Exception as e:
                        logger.info(
                            "No hay más páginas disponibles o el botón no es clickeable."
                        )
                        driver.get(url)
                        continue
                except Exception as e:
                    print(f"Error al procesar resultados: {e}")
                    scraping_failed = True
                    break

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
                    "status": "success",
                    "message": "Los datos han sido scrapeados correctamente.",
                    "data": response_data,
                },
                status=status.HTTP_200_OK,
            )

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response(
            {"status": "error", "message": f"Error durante el scraping: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        driver.quit()
