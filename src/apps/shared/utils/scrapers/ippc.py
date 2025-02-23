from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import urljoin
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)


def scraper_ippc(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"🚀 Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    urls_found = set()
    urls_scraped = set()
    urls_not_scraped = set()

    try:
        driver.get(url)
        logger.info("🌐 Ingresando a la URL principal")

        try:
            select_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "publications_length"))
            )
            select = Select(select_element)

            options = select.options
            if options:
                last_value = options[-1].get_attribute("value")
                select.select_by_value(last_value)

            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#publications tr"))
            )
            logger.info("✅ Datos cargados correctamente en la tabla.")

        except TimeoutException:
            logger.error("⏳ Error: El elemento no se cargó en el tiempo esperado.")
            return Response(
                {"error": "Timeout al cargar los datos"},
                status=status.HTTP_408_REQUEST_TIMEOUT,
            )

        except NoSuchElementException:
            logger.error("❌ Error: No se encontró el elemento <select>.")
            return Response(
                {"error": "No se encontró el select de opciones"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("#publications tr")

        if not rows:
            logger.warning("⚠️ No se encontraron filas en la tabla de publicaciones.")
            return Response(
                {"status": "no_content", "message": "No hay publicaciones disponibles"},
                status=status.HTTP_204_NO_CONTENT,
            )

        for row_index, row in enumerate(rows, start=1):
            tds = row.find_all("td")
            for td in tds:
                link = td.find("a", href=True)
                if link:
                    href = urljoin(url, link["href"])

                    if href in urls_found:
                        continue  # Evita procesar la misma URL varias veces

                    urls_found.add(href)
                    logger.info(f"🔗 URL encontrada: {href}")

                    try:
                        driver.get(href)
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                        )

                        page_soup = BeautifulSoup(driver.page_source, "html.parser")
                        page_title = page_soup.select_one("#divmainbox > h1")
                        page_content = page_soup.select_one("dl.dl-horizontal")

                        if page_title and page_content:
                            page_text = f"{page_title.get_text(strip=True)}\n{page_content.get_text(strip=True)}"

                            object_id = fs.put(
                                page_text.encode("utf-8"),
                                source_url=href,
                                scraping_date=datetime.now(),
                                Etiquetas=["plantas", "algas"],
                                contenido=page_text,
                                url=url,
                            )

                            urls_scraped.add(href)
                            logger.info(
                                f"✅ Contenido almacenado en MongoDB con ID: {object_id}"
                            )
                            existing_versions = list(
                                fs.find({"source_url": href}).sort("scraping_date", -1)
                            )

                            if len(existing_versions) > 1:
                                oldest_version = existing_versions[-1]
                                fs.delete(oldest_version._id)  
                                logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version.id}")


                        else:
                            logger.warning(f"⚠️ No se extrajo contenido de {href}")
                            urls_not_scraped.add(href)

                    except Exception as e:
                        logger.error(f"❌ Error al procesar {href}: {e}")
                        urls_not_scraped.add(href)

                    # Volver a la tabla principal
                    driver.back()
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "#publications tr")
                        )
                    )

        # 📝 Generar reporte final
        all_scraper = (
            f"📌 **Reporte de scraping:**\n"
            f"🌐 URL principal: {url}\n"
            f"🔍 URLs encontradas: {len(urls_found)}\n"
            f"✅ URLs scrapeadas: {len(urls_scraped)}\n"
            f"⚠️ URLs no scrapeadas: {len(urls_not_scraped)}\n\n"
        )

        if urls_scraped:
            all_scraper += (
                "✅ **URLs scrapeadas:**\n" + "\n".join(urls_scraped) + "\n\n"
            )

        if urls_not_scraped:
            all_scraper += (
                "⚠️ **URLs no scrapeadas:**\n" + "\n".join(urls_not_scraped) + "\n"
            )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"❌ Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado.")
