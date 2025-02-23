from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
from urllib.parse import urljoin
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)


def scraper_se_eppc(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"🚀 Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    urls_found = set()
    urls_scraped = set()
    urls_not_scraped = set()

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.content1 table tbody")
            )
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tr_tags = soup.select("div.content1 table tbody tr")

        if not tr_tags:
            logger.warning("⚠️ No se encontraron filas <tr> en la tabla.")
            return Response(
                {
                    "status": "no_content",
                    "message": "No se encontraron filas en la tabla.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )

        for index, tr in enumerate(tr_tags[1:], start=2):
            try:
                first_td = tr.select_one("td:first-child a")
                if first_td:
                    href = first_td.get("href")
                    if href:
                        href = urljoin(url, href)

                        if href in urls_found:
                            continue  # Evitar procesar la misma URL más de una vez

                        urls_found.add(href)
                        logger.info(f"🔗 URL encontrada: {href}")

                        driver.get(href)
                        time.sleep(5)

                        try:
                            about_tab = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable(
                                    (By.LINK_TEXT, "About This Subject")
                                )
                            )
                            driver.execute_script("arguments[0].click();", about_tab)
                            time.sleep(3)
                        except Exception as e:
                            logger.warning(
                                f"⚠️ No se pudo hacer clic en 'About This Subject' en {href}: {e}"
                            )
                            urls_not_scraped.add(href)
                            continue

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        container = soup.select_one("div.container")

                        if container:
                            overview = container.select_one("#overview")

                            if overview:
                                page_text = overview.get_text(
                                    separator="\n", strip=True
                                )
                                if page_text:
                                    object_id = fs.put(
                                        page_text.encode("utf-8"),
                                        source_url=href,
                                        scraping_date=datetime.now(),
                                        Etiquetas=["planta", "plaga"],
                                        contenido=page_text,
                                        url=url,
                                    )

                                    urls_scraped.add(href)
                                    logger.info(
                                        f"✅ Contenido almacenado en MongoDB con ID: {object_id}"
                                    )
                                    existing_versions = list(
                                        fs.find({"source_url": href}).sort(
                                            "scraping_date", -1
                                        )
                                    )

                                    if len(existing_versions) > 1:
                                        oldest_version = existing_versions[-1]
                                        fs.delete(oldest_version._id)  
                                        logger.info(
                                            f"🗑️ Se eliminó la versión más antigua con object_id: {oldest_version['_id']}"
                                        )

                                else:
                                    logger.warning(
                                        f"⚠️ El contenido de #overview en {href} está vacío."
                                    )
                                    urls_not_scraped.add(href)
                            else:
                                logger.warning(
                                    f"⚠️ No se encontró #overview dentro de div.container en {href}."
                                )
                                urls_not_scraped.add(href)
                        else:
                            logger.warning(
                                f"⚠️ No se encontró 'div.container' en {href}."
                            )
                            urls_not_scraped.add(href)

            except Exception as e:
                logger.error(f"❌ Error al procesar el enlace {href}: {e}")
                urls_not_scraped.add(href)

        all_scraper = (
            f"📌 **Reporte de scraping:**\n"
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
