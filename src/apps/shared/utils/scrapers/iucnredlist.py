from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
import random

def scraper_iucnredlist(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    visited_urls = set()
    
    try:
        driver.get(url)
        logger.info("Página cargada correctamente")

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#page"))
        )
        logger.info("Elemento #page encontrado")

        button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search--site__button"))
        )
        driver.execute_script("arguments[0].click();", button)
        logger.info("Botón de búsqueda clickeado")

        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.cards--narrow article")
            )
        )
        logger.info("Artículos encontrados en la página")

        while True:
            articles = driver.find_elements(
                By.CSS_SELECTOR, "div.cards--narrow article a"
            )
            logger.info(f"Se encontraron {len(articles)} artículos en la página")

            for index, article in enumerate(articles):
                href = article.get_attribute("href")
                logger.info(f"Procesando artículo {index+1}: {href}")

                if href in visited_urls:
                    logger.info(f"URL ya visitada: {href}, omitiendo...")
                    continue

                driver.get(href)
                logger.info(f"Cargando contenido de: {href}")

                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                try:
                    title = taxonomy = habitat = ""
                    
                    try:
                        title = WebDriverWait(driver, 30).until(
                            lambda d: d.find_element(
                                By.CSS_SELECTOR,
                                "h1.headline__title",
                            ).text.strip()
                        )
                        logger.info(f"Título obtenido: {title}")
                    except Exception as e:
                        logger.error(f"Error al obtener el título: {e}")
                    
                    try:
                        taxonomy = WebDriverWait(driver, 30).until(
                            lambda d: d.find_element(
                                By.CSS_SELECTOR, "#taxonomy"
                            ).text.strip()
                        )
                        logger.info("Taxonomía obtenida correctamente")
                    except Exception as e:
                        logger.error(f"Error al obtener la taxonomía: {e}")
                    
                    try:
                        habitat = WebDriverWait(driver, 30).until(
                            lambda d: d.find_element(
                                By.CSS_SELECTOR, "#habitat-ecology"
                            ).text.strip()
                        )
                        logger.info("Hábitat obtenido correctamente")
                    except Exception as e:
                        logger.error(f"Error al obtener el hábitat: {e}")

                    text_content = title + taxonomy + habitat
                    if text_content:
                        all_scraper += text_content
                        logger.info("Contenido del artículo almacenado")
                except Exception as e:
                    logger.error(f"Error procesando el artículo {href}: {e}")
                
                visited_urls.add(href)
                time.sleep(random.randint(1, 3))
                driver.back()
                logger.info("Regresando a la página principal")

            try:
                show_more_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".section__link-out"))
                )
                driver.execute_script("arguments[0].click();", show_more_btn)
                logger.info("Botón 'Show More' clickeado, cargando más artículos...")

                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div.cards--narrow article")
                    )
                )
            except Exception as e:
                logger.info("No hay más artículos para cargar, terminando scraping.")
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response
    except Exception as e:
        logger.error(f"Error en el scraper: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        driver.quit()
        logger.info("Driver cerrado correctamente")
