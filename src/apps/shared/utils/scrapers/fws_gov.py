from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)


def scraper_fws_gov(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    base_url = "https://www.fws.gov"

    try:
        driver.get(url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.default-view"))
            )
        except Exception as e:
            logger.error(f"Error al cargar la página principal: {e}")
            return Response({"error": f"Error al cargar la página principal: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        while True:
            try:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                cards = soup.select("div.default-view mat-card")

                if not cards:
                    logger.warning("No se encontraron tarjetas en la página.")
                    break

                logger.info(f"Se encontraron {len(cards)} tarjetas para procesar.")

                for card in cards:
                    try:
                        link = card.find("a", href=True)
                        if not link:
                            logger.warning("No se encontró enlace en la tarjeta.")
                            continue

                        card_url = link["href"]
                        title = card.select_one("span")
                        title_text = title.text.strip() if title else "Sin título"

                        all_scraper += f"{title_text}\n"
                        full_url = base_url + card_url

                        try:
                            driver.get(full_url)

                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )

                            soup_page = BeautifulSoup(driver.page_source, "html.parser")
                            content = soup_page.select_one("div.layout-stacked-side-by-side")

                            if content:
                                all_scraper += content.get_text(separator="\n", strip=True)
                                all_scraper += "\n\n"

                        except Exception as e:
                            logger.error(f"Error al extraer contenido de {full_url}: {e}")
                            continue

                        try:
                            driver.back()
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.default-view"))
                            )
                        except Exception as e:
                            logger.warning(f"Error al regresar a la página anterior: {e}")
                            driver.get(url)  
                            time.sleep(2)

                    except Exception as e:
                        logger.error(f"Error al procesar tarjeta: {e}")
                        continue  

            except Exception as e:
                logger.error(f"Error al procesar la página: {e}")
                break 

            try:
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".search-pager__item"))
                )
                driver.execute_script("arguments[0].click();", next_page_button)
                time.sleep(3)

            except Exception as e:
                logger.warning(f"No se encontró botón de siguiente página o error al hacer clic: {e}")
                break  

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado correctamente.")
