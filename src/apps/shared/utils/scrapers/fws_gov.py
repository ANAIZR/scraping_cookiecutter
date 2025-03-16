from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    save_to_mongo
)
import time
import random
import traceback

def scraper_fws_gov(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = driver_init()
    collection, fs = connect_to_mongo()
    base_url = "https://www.fws.gov"

    total_urls_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    urls_not_scraped = []
    urls_scraped = []
    object_ids = []
    all_scraper = ""

    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.default-view"))
            )
            logger.info("✅ Página principal cargada correctamente.")
        except Exception as e:
            error_message = f"❌ Error al cargar la página principal: {e}"
            logger.error(error_message)
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        while True:
            logger.info(f"📄 Procesando página con URL: {driver.current_url}")
            try:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                cards = soup.select("div.default-view mat-card")
                if not cards:
                    logger.warning("⚠ No se encontraron tarjetas en la página.")
                    break
                logger.info(f"🔍 Se encontraron {len(cards)} tarjetas en la página actual.")
                total_urls_found += len(cards)

                for index, card in enumerate(cards, start=1):
                    try:
                        link = card.find("a", href=True)
                        if not link:
                            logger.warning(f"⚠ Tarjeta {index} no tiene enlace. Omitiendo...")
                            continue
                        card_url = link["href"]
                        title = card.select_one("span")
                        title_text = title.text.strip() if title else "Sin título"
                        full_url = base_url + card_url

                        logger.info(f"📌 Procesando tarjeta {index}: {title_text} - {full_url}")

                        try:
                            driver.get(full_url)
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                            logger.info(f"✅ Página cargada correctamente: {full_url}")

                            soup_page = BeautifulSoup(driver.page_source, "html.parser")
                            content = soup_page.select_one("div.layout-stacked-side-by-side")

                            if content:
                                page_text = content.get_text(separator="\n", strip=True)
                                if page_text:

                                    object_id = save_to_mongo("urls_scraper", page_text, full_url, url)
                                    total_scraped_successfully += 1
                                    urls_scraped.append(full_url)
                                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                    
                                else:
                                    logger.warning(f"⚠ Contenido vacío en {full_url}")
                                    urls_not_scraped.append(full_url)
                                    total_failed_scrapes += 1
                            else:
                                logger.warning(f"⚠ No se encontró 'layout-stacked-side-by-side' en {full_url}")
                                urls_not_scraped.append(full_url)
                                total_failed_scrapes += 1

                        except Exception as e:
                            logger.error(f"❌ Error al extraer contenido de {full_url}: {e}")
                            logger.error(traceback.format_exc())
                            urls_not_scraped.append(full_url)
                            total_failed_scrapes += 1
                            continue

                        try:
                            driver.back()
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.default-view"))
                            )
                            logger.info(f"↩ Regresó correctamente a la página con URL: {driver.current_url}")
                        except Exception as e:
                            logger.warning(f"⚠ Error al regresar a la página anterior: {e}")
                            driver.get(url)
                            time.sleep(2)

                    except Exception as e:
                        logger.error(f"❌ Error al procesar tarjeta {index}: {e}")
                        logger.error(traceback.format_exc())
                        continue

            except Exception as e:
                logger.error(f"❌ Error procesando la página {driver.current_url}: {e}")
                logger.error(traceback.format_exc())
                break

            current_url = driver.current_url
            if "$skip=100" in current_url:
                print("¡Hasta aquí termina el paginator! (skip=100)")
                break

            try:
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.search-pager__item.search-pager__item--next.search-pager-link.mat-icon-button"))
                )
                driver.execute_script("arguments[0].click();", next_page_button)
                time.sleep(3)
                logger.info(f"///Avanzando a la siguiente página: {driver.current_url}")
            except Exception as e:
                logger.warning(f"⚠ No se encontró botón de siguiente página o error al hacer clic: {e}")
                break

        all_scraper += f"Total enlaces encontrados: {total_urls_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(urls_scraped) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)        
        return response


    except Exception as e:
        logger.error(f"❌ Error general durante el scraping: {e}")
        logger.error(traceback.format_exc())
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("✅ Navegador cerrado correctamente.")