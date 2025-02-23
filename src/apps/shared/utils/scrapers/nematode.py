from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bson.objectid import ObjectId
from datetime import datetime
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_nematode(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    content_text = ""  # Para almacenar toda la data en MongoDB
    all_scraper = ""  # Para generar un reporte del scraping
    total_records_found = 0  # Total de registros encontrados
    total_scraped_successfully = 0  # Total de registros scrapeados
    total_failed_scrapes = 0  # Total de registros que fallaron

    try:
        driver.get(url)
        all_scraper += f"Página principal: {url}\n\n"

        while True:
            content = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.view"))
            )

            rows = driver.find_elements(By.CSS_SELECTOR, "div.views-row")
            total_records_found += len(rows)  # Contamos cuántos registros hay en la página

            for index, row in enumerate(rows, start=1):
                try:
                    fields = row.find_elements(By.CSS_SELECTOR, "div.content div.field--label-inline")
                    for field in fields:
                        label = field.find_element(By.CSS_SELECTOR, "div.field--label").text.strip()

                        field_items = []
                        spans = field.find_elements(By.CSS_SELECTOR, "span")
                        for span in spans:
                            text = span.text.strip()
                            if text and text not in field_items:
                                field_items.append(text)

                        divs = field.find_elements(By.CSS_SELECTOR, "div.field--item")
                        for div in divs:
                            text = div.text.strip()
                            if text and text not in field_items:
                                field_items.append(text)

                        field_text = " ".join(field_items).strip()
                        content_text += f"{label}: {field_text}\n"
                    content_text += "\n"

                    # Procesar enlaces dentro del registro
                    links = row.find_elements(By.CSS_SELECTOR, "a")
                    for link in links:
                        link_href = link.get_attribute("href")
                        if link_href:
                            driver.get(link_href)
                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                            page_text = driver.find_element(By.TAG_NAME, "body").text.strip()

                            if page_text:

                                object_id = fs.put(
                                    page_text.encode("utf-8"),
                                    source_url=link_href,
                                    scraping_date=datetime.now(),
                                    Etiquetas=["planta", "plaga"],
                                    contenido=page_text,
                                    url=url
                                )
                                total_scraped_successfully += 1
                                logger.info(f"📌 Documento almacenado en MongoDB con object_id: {object_id}")

                                # Eliminar versiones antiguas y mantener solo la más reciente
                                existing_versions = list(fs.find({"source_url": link_href}).sort("scraping_date", -1))
                                if len(existing_versions) > 1:
                                    oldest_version = existing_versions[-1]
                                    fs.delete(oldest_version._id)  
                                    logger.info(f"🗑 Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")

                except Exception as e:
                    logger.error(f"❌ Error en el registro {index}: {e}")
                    total_failed_scrapes += 1
                    continue  # Continuar con la siguiente fila en caso de error

            # Intentar ir a la siguiente página
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[title='Go to next page']"))
                )
                next_button_class = next_button.get_attribute("class")
                if "disabled" in next_button_class or "is-active" in next_button_class:
                    break
                else:
                    next_button.click()
                    WebDriverWait(driver, 10).until(EC.staleness_of(content))
            except Exception:
                break  # No hay más páginas disponibles

        # Generar reporte final
        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de registros encontrados: {total_records_found}\n"
            f"Total de registros scrapeados: {total_scraped_successfully}\n"
            f"Total de registros fallidos: {total_failed_scrapes}\n\n"
            f"{'-'*80}\n\n"
        )

        

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        return Response({"error": f"Ocurrió un error durante el scraping: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("✅ Navegador cerrado.")
