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
)
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("scraper")


def load_keywords(file_path="../txt/plants.txt"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(base_path, file_path)
        with open(absolute_path, "r", encoding="utf-8") as f:
            keywords = [
                line.strip() for line in f if isinstance(line, str) and line.strip()
            ]
        logger.info(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        logger.error(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise


def scraper_sciencedirect(url, sobrenombre):
    try:
        driver = initialize_driver()
        try:
            driver.get(url)
            time.sleep(random.uniform(6, 10))

            collection, fs = connect_to_mongo("scrapping-can", "collection")
            main_folder = generate_directory(url)
            keywords = load_keywords()
            visited_urls = set()
            scraping_failed = False
        except Exception as e:
            logger.error(f"Error al inicializar el scraper: {str(e)}")
            return Response(
                {"message": f"Error al inicializar el scraper: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        for keyword in keywords:
            logger.info(f"Buscando con la palabra clave: {keyword}")
            keyword_folder = generate_directory(keyword, main_folder)
            try:
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "qs"))
                )
                search_input.clear()
                search_input.send_keys(keyword)

                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button"))
                )
                search_button.click()
                time.sleep(random.uniform(3, 6))
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                scraping_failed = True
                continue

            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.ID, "srp-results-list"))
                    )
                    results_list = driver.find_elements(By.CSS_SELECTOR, "#srp-results-list a")

                    urls = [
                        result.get_attribute("href")
                        for result in results_list
                        if result.get_attribute("href") 
                            and result.get_attribute("href").lower().startswith("https://www.sciencedirect.com/science/article/pii")
                            and not result.get_attribute("href").lower().endswith(".pdf")
                    ]
                    logger.info(f"{len(urls)} resultados filtrados para procesar.")

                    for absolut_href in urls:
                        if absolut_href in visited_urls:
                            continue

                        driver.get(absolut_href)
                        visited_urls.add(absolut_href)
                        WebDriverWait(driver, 60).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                        )
                        time.sleep(random.uniform(6, 10))

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        abstract_text = soup.select_one("#abstracts").get_text(strip=True) if soup.select_one("#abstracts") else "No abstract found"
                        body_text = soup.select_one("#screen-reader-main-title").get_text(strip=True) if soup.select_one("#screen-reader-main-title") else ""

                        if abstract_text and body_text:
                            contenido = f"{abstract_text}\n\n\n{body_text}"
                            link_folder = generate_directory(absolut_href, keyword_folder)
                            file_path = get_next_versioned_filename(link_folder, keyword)
                            with open(file_path, "w", encoding="utf-8") as file:
                                file.write(contenido)

                            with open(file_path, "rb") as file_data:
                                object_id = fs.put(
                                    file_data, filename=os.path.basename(file_path)
                                )

                            logger.info(f"Página procesada y guardada: {absolut_href}")
                        else:
                            logger.info("No se encontró contenido en la página.")
                        driver.back()
                        time.sleep(random.uniform(3, 6))

                    try:
                        next_page_button = driver.find_element(By.CSS_SELECTOR, "a.anchor[data-aa-name='srp-next-page']")

                        next_page_link = next_page_button.get_attribute("href")

                        if next_page_link:
                            logger.info(f"Yendo a la siguiente página: {next_page_link}")
                            driver.get(next_page_link)
                            time.sleep(random.uniform(3, 6))
                        else:
                            logger.info("No hay más páginas disponibles. Finalizando búsqueda para esta palabra clave.")
                            break
                    except NoSuchElementException:
                        logger.info("No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave.")
                        break
                except Exception as e:
                    logger.error(f"Error al procesar resultados: {e}")
                    scraping_failed = True
                    break
            driver.get(url)

        if scraping_failed:
            return Response(
                {"message": "Error durante el scraping. Algunas URLs fallaron."},
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
            collection.insert_one(data)
            delete_old_documents(url, collection, fs)

            return Response(
                {"data": data, "message": "Scraping completado con éxito."},
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