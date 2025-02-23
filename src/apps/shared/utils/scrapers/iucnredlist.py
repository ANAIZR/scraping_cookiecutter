from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
import random
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_iucnredlist(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"🚀 Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    urls_found = set()
    urls_scraped = set()
    urls_not_scraped = set()

    try:
        driver.get(url)
        logger.info("🌐 Página cargada correctamente")

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#page"))
        )
        logger.info("✅ Elemento #page encontrado")

        # Hacer clic en el botón de búsqueda
        try:
            button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search--site__button"))
            )
            driver.execute_script("arguments[0].click();", button)
            logger.info("🔎 Botón de búsqueda clickeado")
        except Exception as e:
            logger.error(f"❌ No se pudo hacer clic en el botón de búsqueda: {e}")

        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.cards--narrow article"))
        )
        logger.info("📄 Artículos encontrados en la página")

        while True:
            articles = driver.find_elements(By.CSS_SELECTOR, "div.cards--narrow article a")
            logger.info(f"🔍 Se encontraron {len(articles)} artículos en la página")

            for article in articles:
                href = article.get_attribute("href")

                if href in urls_found:
                    logger.info(f"🔄 URL ya procesada: {href}, omitiendo...")
                    continue

                urls_found.add(href)
                logger.info(f"🔗 URL encontrada: {href}")

                try:
                    driver.get(href)
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    title = taxonomy = habitat = ""

                    try:
                        title = WebDriverWait(driver, 10).until(
                            lambda d: d.find_element(By.CSS_SELECTOR, "h1.headline__title").text.strip()
                        )
                        logger.info(f"✅ Título obtenido: {title}")
                    except Exception:
                        logger.warning(f"⚠️ No se encontró el título en {href}")

                    try:
                        taxonomy = WebDriverWait(driver, 10).until(
                            lambda d: d.find_element(By.CSS_SELECTOR, "#taxonomy").text.strip()
                        )
                        logger.info("✅ Taxonomía obtenida correctamente")
                    except Exception:
                        logger.warning(f"⚠️ No se encontró la taxonomía en {href}")

                    try:
                        habitat = WebDriverWait(driver, 10).until(
                            lambda d: d.find_element(By.CSS_SELECTOR, "#habitat-ecology").text.strip()
                        )
                        logger.info("✅ Hábitat obtenido correctamente")
                    except Exception:
                        logger.warning(f"⚠️ No se encontró el hábitat en {href}")

                    text_content = "\n".join([title, taxonomy, habitat]).strip()

                    if text_content:
                        object_id = fs.put(
                            text_content.encode("utf-8"),
                            source_url=href,
                            scraping_date=datetime.now(),
                            Etiquetas=["IUCN", "Especies"],
                            contenido=text_content,
                            url=url
                        )

                        urls_scraped.add(href)
                        logger.info(f"✅ Contenido almacenado en MongoDB con ID: {object_id}")
                        existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))

                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(ObjectId(oldest_version["_id"]))
                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")
                    else:
                        urls_not_scraped.add(href)
                        logger.warning(f"⚠️ No se extrajo contenido de {href}")

                except Exception as e:
                    logger.error(f"❌ Error procesando {href}: {e}")
                    urls_not_scraped.add(href)

                time.sleep(random.randint(1, 3))
                driver.back()
                logger.info("↩️ Regresando a la página principal")

            try:
                show_more_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".section__link-out"))
                )
                driver.execute_script("arguments[0].click();", show_more_btn)
                logger.info("➡️ Botón 'Show More' clickeado, cargando más artículos...")

                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.cards--narrow article"))
                )
            except Exception:
                logger.info("⏹️ No hay más artículos para cargar, terminando scraping.")
                break

        # 📝 Generar reporte final
        all_scraper = (
            f"📌 **Reporte de scraping:**\n"
            f"🌐 URL principal: {url}\n"
            f"🔍 URLs encontradas: {len(urls_found)}\n"
            f"✅ URLs scrapeadas: {len(urls_scraped)}\n"
            f"⚠️ URLs no scrapeadas: {len(urls_not_scraped)}\n\n"
        )

        if urls_scraped:
            all_scraper += "✅ **URLs scrapeadas:**\n" + "\n".join(urls_scraped) + "\n\n"

        if urls_not_scraped:
            all_scraper += "⚠️ **URLs no scrapeadas:**\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"❌ Error en el scraper: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("🛑 Driver cerrado correctamente")
