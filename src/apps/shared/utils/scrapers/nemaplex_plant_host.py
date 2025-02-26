from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
import time
import random
from datetime import datetime
from bson import ObjectId

def scraper_nemaplex_plant_host(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    all_scraper = ""
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    scraped_urls = set()
    failed_urls = set()
    visited_urls = set()
    object_ids = []

    try:
        driver.get(url)

        # Esperar a que el dropdown aparezca
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "DropDownList1"))
        )

        # Cargar el dropdown
        dropdown = Select(driver.find_element(By.ID, "DropDownList1"))

        # Iterar sobre todas las opciones
        for i in range(len(dropdown.options)):
            try:
                # Reubicar el dropdown en cada iteración (para evitar stale element)
                dropdown = Select(driver.find_element(By.ID, "DropDownList1"))
                option_text = dropdown.options[i].text.strip()
                logger.info(f"📌 Procesando opción {i}: {option_text}")

                total_links_found += 1

                # Seleccionar la opción por índice
                dropdown.select_by_index(i)
                time.sleep(1)

                # Hacer clic en el botón de submit
                submit_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']"))
                )
                driver.execute_script("arguments[0].click();", submit_button)

                # Esperar a que la página cambie de URL o se recargue
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)

                # Obtener la nueva URL
                result_url = driver.current_url

                # ⚡ Evitar URLs duplicadas
                if result_url not in visited_urls:
                    visited_urls.add(result_url)
                    scraped_urls.add(result_url)
                    logger.info(f"✅ URL extraída: {result_url}")

                # Extraer el contenido de la tabla o mostrar "No tiene información disponible"
                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                table = page_soup.find("table", {"id": "GridView1"})

                if table:
                    content_text = table.get_text(separator="\n", strip=True)
                    logger.info(f"✅ Se encontró tabla con datos para {option_text}")
                else:
                    content_text = "No tiene información disponible"
                    logger.warning(f"⚠️ No se encontró la tabla en {result_url}")

                # **Guardar en MongoDB**
                try:
                    object_id = fs.put(
                        content_text.encode("utf-8"),
                        source_url=result_url,
                        scraping_date=datetime.now(),
                        Etiquetas=["planta", "plaga"],
                        contenido=content_text,
                        url=url
                    )
                    object_ids.append(object_id)
                    total_scraped_successfully += 1
                    logger.info(f"📂 Archivo almacenado en MongoDB con object_id: {object_id}")

                    # **Eliminar versiones antiguas (si hay más de 2)**
                    existing_versions = list(
                        fs.find({"source_url": result_url}).sort("scraping_date", -1)
                    )

                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        fs.delete(ObjectId(oldest_version["_id"]))
                        logger.info(f"🗑 Se eliminó la versión más antigua de {result_url}")

                    logger.info(f"✅ Contenido extraído y guardado de {result_url}.")

                except Exception as e:
                    logger.error(f"❌ Error al guardar en MongoDB: {e}")
                    total_failed_scrapes += 1
                    failed_urls.add(result_url)
                    scraped_urls.remove(result_url)

                # **Condición de salida**: Si se encuentra "Abelia spathulata Siebold & Zucc.", detener el scraping.
                if option_text == "Abelia spathulata Siebold & Zucc.":
                    logger.info(f"🛑 Se encontró '{option_text}'. Deteniendo el scraper.")
                    break

                # Regresar a la página original para procesar la siguiente opción
                driver.get(url)
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "DropDownList1"))
                )
                time.sleep(2)

            except (TimeoutException, StaleElementReferenceException) as e:
                logger.warning(f"⚠️ Problema con la opción {i} - {option_text}: {str(e)}")
                total_failed_scrapes += 1
                failed_urls.add(url)
                driver.get(url)
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "DropDownList1"))
                )
                time.sleep(2)
                continue
            except Exception as e:
                logger.error(f"❌ Error al extraer datos de la opción {option_text}: {str(e)}")
                total_failed_scrapes += 1
                failed_urls.add(url)
                driver.get(url)
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "DropDownList1"))
                )
                time.sleep(2)
                continue

        # Construcción del reporte final
        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"⚠️ Error general en el scraper: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("🚪 Navegador cerrado.")
