from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_flmnh_ufl(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()

    try:
        collection, fs = connect_to_mongo()
    except Exception as e:
        logger.error(f"Error al conectar a MongoDB: {str(e)}")
        return Response(
            {"error": f"Error al conectar a MongoDB: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    all_scraper = f"{url}\n\n"
    total_scraped_successfully = 0

    def scrape_page():
        nonlocal all_scraper, total_scraped_successfully
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "table.x-grid-table tbody tr")
                )
            )
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows = soup.select("table.x-grid-table tbody tr:not(.x-grid-header-row)")

            for row in rows:
                cols = row.find_all("td")
                data = [col.text.strip() for col in cols]
                all_scraper += " | ".join(data) + "\n"

                # Extraer y procesar enlaces dentro de cada fila
                links = row.find_all("a", href=True)
                for link in links:
                    link_href = link["href"]
                    driver.get(link_href)
                    time.sleep(2)
                    content_soup = BeautifulSoup(driver.page_source, "html.parser")
                    content_text = content_soup.get_text()

                    if content_text:
                        object_id = fs.put(
                            content_text.encode("utf-8"),
                            source_url=link_href,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=content_text,
                            url=url
                        )
                        total_scraped_successfully += 1
                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                        # Gestionar versiones antiguas
                        existing_versions = list(fs.find({"source_url": link_href}).sort("scraping_date", -1))
                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(ObjectId(oldest_version["_id"]))
                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")
        except Exception as e:
            logger.error(f"Error durante el scraping de la página: {str(e)}")
            raise e

    def go_to_next_page():
        try:
            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "button-1065-btnEl"))
            )
            next_button = driver.find_element(By.ID, "button-1065-btnEl")
            driver.execute_script("arguments[0].click();", next_button)
            logger.info("Clic en el botón de siguiente página")
            return True
        except Exception as e:
            logger.warning(
                f"No se pudo hacer clic en el botón de siguiente página: {str(e)}"
            )
            return False

    try:
        driver.get(url)
        logger.info(f"URL cargada: {url}")

        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl"))
        )
        btn = driver.find_element(By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl")
        driver.execute_script("arguments[0].click();", btn)

        scrape_page()

        while go_to_next_page():
            time.sleep(2)
            scrape_page()

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado")
