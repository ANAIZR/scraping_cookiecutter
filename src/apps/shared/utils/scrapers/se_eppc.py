from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
from urllib.parse import urljoin
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_se_eppc(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.content1 table tbody"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tr_tags = soup.select("div.content1 table tbody tr")

        if not tr_tags:
            logger.warning("No se encontraron filas <tr> en la tabla.")
            return Response(
                {"status": "no_content", "message": "No se encontraron filas en la tabla."},
                status=status.HTTP_204_NO_CONTENT
            )

        for index, tr in enumerate(tr_tags[1:], start=2):
            try:
                first_td = tr.select_one("td:first-child a")
                if first_td:
                    href = first_td.get("href")
                    if href:
                        if not href.startswith("http"):
                            href = urljoin(url, href)

                        driver.get(href)
                        time.sleep(5) 

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        container = soup.select_one("div.container")

                        if container:

                            overview = container.select_one("#overview")

                            if overview:
                                page_text = overview.get_text(separator="\n", strip=True)
                                if page_text:
                                    all_scraper += f"\n\nURL: {href}\n{page_text}\n"
                                    logger.info(f"Contenido extraído correctamente de {href}")
                                else:
                                    logger.warning(f"El contenido de #overview en {href} está vacío.")
                            else:
                                logger.warning(f"No se encontró #overview dentro de div.container en {href}. Continuando...")
                        else:
                            logger.warning(f"No se encontró 'div.container' en {href}. Continuando con la siguiente página...")

            except Exception as e:
                logger.error(f"Error al procesar el enlace {href}: {e}")

        if not all_scraper.strip():
            logger.warning(f"No se encontró contenido en las páginas exploradas desde {url}.")
            return Response(
                {"status": "no_content", "message": "No se encontraron datos para scrapear."},
                status=status.HTTP_204_NO_CONTENT
            )

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
