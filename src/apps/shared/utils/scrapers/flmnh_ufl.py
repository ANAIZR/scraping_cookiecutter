from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_flmnh_ufl(
    url,
    sobrenombre,
):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    logger.info("Driver inicializado correctamente.")
    
    try:
        collection, fs = connect_to_mongo("scrapping-can", "collection")
        logger.info("Conexión a MongoDB establecida correctamente.")
    except Exception as e:
        logger.error(f"Error al conectar a MongoDB: {str(e)}")
        return Response({"error": f"Error al conectar a MongoDB: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    all_scraper = ""

    def scrape_page():
        try:
            logger.info("Esperando que los elementos de la página se carguen...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "table.x-grid-table tbody tr")
                )
            )
            logger.info("Elementos de la página encontrados, extrayendo datos.")
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows = soup.select("table.x-grid-table tbody tr:not(.x-grid-header-row)")

            all_scraper_data = []
            for row in rows:
                cols = row.find_all("td")
                data = [col.text.strip() for col in cols]
                all_scraper_data.append(data)
            logger.info(f"Datos extraídos de la página: {len(all_scraper_data)} filas.")
        except Exception as e:
            logger.error(f"Error durante el scraping de la página: {str(e)}")
            raise e

    def go_to_next_page():
        try:
            logger.info("Intentando ir a la siguiente página...")
            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "button-1065-btnEl"))
            )
            next_button = driver.find_element(By.ID, "button-1065-btnEl")
            next_button.click()
            logger.info("Botón de siguiente página clickeado.")
            return True
        except Exception as e:
            logger.warning(f"No se pudo hacer clic en el botón de siguiente página: {str(e)}")
            return False

    try:
        driver.get(url)
        logger.info(f"URL cargada: {url}")

        logger.info("Esperando que el botón de búsqueda avanzada sea clickeable...")
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl"))
        )
        btn = driver.find_element(By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl")
        btn.click()
        logger.info("Botón de búsqueda avanzada clickeado.")

        logger.info("Iniciando scraping de la primera página...")
        scrape_page()

        while go_to_next_page():
            time.sleep(2)
            logger.info("Scrapeando la siguiente página...")
            scrape_page()

        logger.info("Procesando los datos extraídos...")
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        logger.info("Cerrando el driver.")
        driver.quit()
