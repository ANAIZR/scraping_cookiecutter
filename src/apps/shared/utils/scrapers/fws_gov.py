from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import time
import traceback
from bson import ObjectId
from datetime import datetime
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
    base_url = "https://www.fws.gov"

    total_urls_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    urls_not_scraped = []
    urls_scraped = []

    try:
        start_time = time.time()
        driver.get(url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.default-view"))
            )
            logger.info("✅ Página principal cargada correctamente.")
        except Exception as e:
            logger.error(f"❌ Error al cargar la página principal: {e}")
            return Response(
                {"error": f"Error al cargar la página principal: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        page_number = 1

        while True:
            logger.info(f"📄 Procesando página {page_number}...")

            try:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                cards = soup.select("div.default-view mat-card")

                if not cards:
                    logger.warning("⚠ No se encontraron tarjetas en la página.")
                    break

                logger.info(f"🔍 Se encontraron {len(cards)} tarjetas en la página {page_number}.")
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
                                    # Guardar en MongoDB
                                    object_id = fs.put(
                                        page_text.encode("utf-8"),
                                        source_url=full_url,
                                        scraping_date=datetime.now(),
                                        Etiquetas=["fws", "wildlife"],
                                        contenido=page_text,
                                        url=url
                                    )
                                    total_scraped_successfully += 1
                                    urls_scraped.append(full_url)
                                    logger.info(f"📌 Documento almacenado en MongoDB con object_id: {object_id}")

                                    # Eliminar versiones antiguas
                                    existing_versions = list(fs.find({"source_url": full_url}).sort("scraping_date", -1))
                                    if len(existing_versions) > 1:
                                        oldest_version = existing_versions[-1]
                                        fs.delete(ObjectId(oldest_version["_id"]))
                                        logger.info(f"🗑 Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")
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
                            logger.info(f"↩ Regresó correctamente a la página {page_number}.")
                        except Exception as e:
                            logger.warning(f"⚠ Error al regresar a la página anterior: {e}")
                            driver.get(url)
                            time.sleep(2)

                    except Exception as e:
                        logger.error(f"❌ Error al procesar tarjeta {index}: {e}")
                        logger.error(traceback.format_exc())
                        continue

            except Exception as e:
                logger.error(f"❌ Error al procesar la página {page_number}: {e}")
                logger.error(traceback.format_exc())
                break

            try:
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".search-pager__item"))
                )
                driver.execute_script("arguments[0].click();", next_page_button)
                time.sleep(3)
                page_number += 1
                logger.info(f"➡ Avanzando a la página {page_number}...")

            except Exception as e:
                logger.warning(f"⚠ No se encontró botón de siguiente página o error al hacer clic: {e}")
                break

        end_time = time.time()
        elapsed_time = round(end_time - start_time, 2)
        logger.info(f"✅ Scraping completado en {elapsed_time} segundos.")

        all_scraper = (
            f"📊 Resumen del scraping:\n"
            f"🔹 Total de URLs encontradas: {total_urls_found}\n"
            f"✅ Total de URLs scrapeadas: {total_scraped_successfully}\n"
            f"❌ Total de URLs no scrapeadas: {total_failed_scrapes}\n\n"
        )

        if urls_scraped:
            all_scraper += "📂 URLs scrapeadas:\n" + "\n".join(urls_scraped) + "\n\n"

        if urls_not_scraped:
            all_scraper += "⚠ URLs no procesadas:\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"❌ Error general durante el scraping: {e}")
        logger.error(traceback.format_exc())
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("✅ Navegador cerrado correctamente.")
