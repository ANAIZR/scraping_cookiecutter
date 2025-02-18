from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
    process_scraper_data
)
from rest_framework.response import Response
from rest_framework import status
from ..credentials import login_cabi_scienceconnect
from bson import ObjectId

from datetime import datetime

logger = get_logger("scraper")


def scraper_cabi_digital(url, sobrenombre):
    driver = initialize_driver()
    total_scraped_links = 0

    scraped_urls = []
    non_scraped_urls = []
    try:
        if login_cabi_scienceconnect(driver):
            print("Login completado, continuando con el scraping...")
    except:
        logger.error("No se encontró el login")

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
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

        logger.info("Página de CABI cargada exitosamente.")

        base_domain = "https://www.cabidigitallibrary.org"
        visited_urls = set()

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")

            try:
                driver.get(url)
                time.sleep(random.uniform(6, 10))

                search_input = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "#AllFieldb117445f-c250-4d14-a8d9-7c66d5b6a4800",
                        )
                    )
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                search_input.submit()

                logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                continue

            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.rlist li"))
                    )
                    logger.info("Resultados encontrados en la página.")
                    time.sleep(random.uniform(1, 3))

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("ul.rlist li")
                    if not items:
                        logger.warning(
                            f"No se encontraron resultados para la palabra clave: {keyword}"
                        )
                        break

                    for item in items:
                        link = item.find("a")
                        if link and "href" in link.attrs:
                            href = link["href"]
                            if href.startswith("/doi/10.1079/cabicompendium"):
                                absolut_href = f"{base_domain}{href}"

                                try:
                                    driver.get(absolut_href)
                                    visited_urls.add(absolut_href)

                                    WebDriverWait(driver, 60).until(
                                        EC.presence_of_element_located(
                                            (By.CSS_SELECTOR, "body")
                                        )
                                    )
                                    time.sleep(random.uniform(6, 10))
                                    soup = BeautifulSoup(
                                        driver.page_source, "html.parser"
                                    )

                                    abstracts = soup.select_one("#abstracts")
                                    body = soup.select_one(
                                        "#bodymatter>.core-container"
                                    )
                                    abstract_text = (
                                        abstracts.get_text(strip=True)
                                        if abstracts
                                        else "No abstract found"
                                    )
                                    body_text = (
                                        body.get_text(strip=True)
                                        if body
                                        else "No body found"
                                    )

                                    if abstract_text or body_text:
                                        content_accumulated = (
                                            f"{abstract_text}\n\n\n{body_text}"
                                        )
                                        content_accumulated += "-" * 100 + "\n\n"
                                        if content_accumulated:
                                            object_id = fs.put(
                                                content_accumulated.encode("utf-8"),
                                                source_url=absolut_href,
                                                scraping_date=datetime.now(),
                                                Etiquetas=["planta", "plaga"],
                                                contenido=content_accumulated,
                                                url=url,
                                            )
                                            total_scraped_links += 1
                                            scraped_urls.append(absolut_href)
                                            logger.info(
                                                f"Archivo almacenado en MongoDB con object_id: {object_id}"
                                            )

                                            collection.insert_one(
                                                {
                                                    "_id": object_id,
                                                    "source_url": absolut_href,
                                                    "scraping_date": datetime.now(),
                                                    "Etiquetas": ["planta", "plaga"],
                                                    "contenido": content_accumulated,
                                                    "url": url,
                                                }
                                            )

                                            existing_versions = list(
                                                collection.find(
                                                    {"source_url": absolut_href}
                                                ).sort("scraping_date", -1)
                                            )

                                            if len(existing_versions) > 1:
                                                oldest_version = existing_versions[-1]
                                                fs.delete(
                                                    ObjectId(oldest_version["_id"])
                                                )
                                                collection.delete_one(
                                                    {
                                                        "_id": ObjectId(
                                                            oldest_version["_id"]
                                                        )
                                                    }
                                                )
                                                logger.info(
                                                    f"Se eliminó la versión más antigua con este enlace: '{absolut_href}' y object_id: {oldest_version['_id']}"
                                                )
                                        else:
                                            non_scraped_urls.append(absolut_href)

                                        print(
                                            f"Página procesada y guardada: {absolut_href}"
                                        )

                                except Exception as e:
                                    logger.error(
                                        f"Error al procesar la URL {absolut_href}: {e}"
                                    )

                                finally:
                                    try:
                                        driver.back()
                                        WebDriverWait(driver, 30).until(
                                            EC.presence_of_element_located(
                                                (By.CSS_SELECTOR, "ul.rlist li")
                                            )
                                        )
                                        time.sleep(random.uniform(3, 6))
                                    except Exception as e:
                                        logger.error(
                                            f"Error al volver atrás en la navegación: {e}"
                                        )

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
                            continue
                    except NoSuchElementException:
                        logger.info(
                            "No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave."
                        )
                        driver.get(url)
                        continue
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

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
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
