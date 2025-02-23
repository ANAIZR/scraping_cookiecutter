from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
import os
from datetime import datetime
from bson import ObjectId
from ..functions import (
    connect_to_mongo,
    get_logger,
    initialize_driver,
    process_scraper_data
)


def scraper_ndrs_org(url, sobrenombre):
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    logger = get_logger("scraper")
    base_url = "https://www.ndrs.org.uk/"

    urls_found = set()
    urls_scraped = set()
    urls_not_scraped = set()

    try:
        driver.get(url)
        logger.info("🌐 Página de NDRS cargada exitosamente")

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        containers = soup.select("#MainContent .volumes .column")

        if not containers:
            logger.warning("⚠️ No se encontraron volúmenes de publicaciones")
            driver.quit()
            return Response(
                {"message": "No se encontraron volúmenes en la página"},
                status=status.HTTP_204_NO_CONTENT,
            )

        for container in containers:
            title = (
                container.select_one("h2").text.strip()
                if container.select_one("h2")
                else "No Title"
            )

            enlace = (
                container.select_one("a")["href"] if container.select_one("a") else None
            )
            if enlace:
                container_url = base_url + enlace
                driver.get(container_url)

                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )

                time.sleep(3)
                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                article_list = page_soup.select("ul.clist li a")

                if not article_list:
                    continue

                for article in article_list:
                    article_title = article.text.strip()
                    article_url = article["href"]
                    article_full_url = base_url + article_url

                    if article_full_url in urls_found:
                        continue  # Evita procesar la misma URL más de una vez

                    urls_found.add(article_full_url)
                    logger.info(f"🔗 URL encontrada: {article_full_url}")

                    driver.get(article_full_url)
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                    )

                    article_soup = BeautifulSoup(driver.page_source, "html.parser")
                    body_text = article_soup.select_one("#repbody")

                    if body_text:
                        contenido = body_text.text.strip()

                        # Guardar en MongoDB
                        object_id = fs.put(
                            contenido.encode("utf-8"),
                            source_url=article_full_url,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=contenido,
                            url=url,
                        )

                        urls_scraped.add(article_full_url)
                        logger.info(
                            f"✅ Contenido almacenado en MongoDB con ID: {object_id}"
                        )
                        existing_versions = list(
                            fs.find({"source_url": article_full_url}).sort(
                                "scraping_date", -1
                            )
                        )
                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(oldest_version._id)  
                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version.id}")

                    else:
                        urls_not_scraped.add(article_full_url)
                        logger.warning(
                            f"⚠️ No se extrajo contenido de {article_full_url}"
                        )

                driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent"))
                )
                time.sleep(3)

    except Exception as e:
        logger.error(f"❌ Ocurrió un error: {e}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado")

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
        all_scraper += (
            "⚠️ **URLs no scrapeadas:**\n" + "\n".join(urls_not_scraped) + "\n"
        )

    response = process_scraper_data(all_scraper, url, sobrenombre)
         

    return response
