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
)
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("scraper")


def load_keywords(file_path="../txt/all.txt"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(base_path, file_path)
        with open(absolute_path, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]
        logger.info(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        logger.error(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise


def scraper_biota_nz(url, sobrenombre):
    driver = initialize_driver()

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
        collection, fs = connect_to_mongo("scrapping-can", "collection")
        main_folder = generate_directory(url)

        keywords = load_keywords()
        visited_urls = set()
        scraping_failed = False
        logger.info("Página de BIOTA NZ cargada exitosamente.")

        # Localizar la barra de búsqueda en Google Académico

        for keyword in keywords:
            print(f"Buscando la palabra clave: {keyword}")
            keyword_folder = generate_directory(main_folder, keyword)
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
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "list-result"))
                    )
                    logger.info(f"Resultados cargados para: {keyword}")
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("div.row-separation div.col-12.a")

                    print(f"Encontrados {len(items)} resultados.")

                    for item in items:
                        href = item.find("a")["href"]
                        print(f"Enlace encontrado: {href}")
                        if href:
                            logger.info(f"Accediendo al enlace: {href}")

                            driver.get(href)
                            visited_urls.add(href)
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "div.page-content-wrapper")
                                )  
                            )
                            time.sleep(random.uniform(6, 10))
                            soup = BeautifulSoup(driver.page_source, "html.parser")
                            body = soup.select_one("div.page-content-wrapper")
                            body_text = (
                                body.get_text(strip=True) if body else "No body found"
                            )
                            if body_text:
                                contenido = f"{body_text}\n\n\n"
                                link_folder = generate_directory(keyword_folder, href)
                                file_path = get_next_versioned_filename(
                                    link_folder, base_name=sobrenombre
                                )
                                with open(file_path, "w", encoding="utf-8") as file:
                                    file.write(contenido)

                                with open(file_path, "rb") as file_data:
                                    object_id = fs.put(
                                        file_data, filename=os.path.basename(file_path)
                                    )

                                print(f"Página procesada y guardada: {href}")
                            else:
                                print("No se encontró contenido en la página.")
                            driver.back()
                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.ID, "list-result"))
                            )
                            time.sleep(random.uniform(3, 6))
                    try:
                        next_page = driver.find_element_by_css_selector(
                            "a.next.page-numbers"
                        )
                        next_page.click()
                        time.sleep(random.uniform(6, 10))
                    except Exception as e:
                        logger.info("No hay más páginas disponibles.")
                        break
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
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            collection.insert_one(data)
            delete_old_documents(url, collection, fs)
            response = Response(data, status=status.HTTP_200_OK)
            return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return {"status": "error", "message": f"Error durante el scraping: {str(e)}"}
    finally:
        driver.quit()
