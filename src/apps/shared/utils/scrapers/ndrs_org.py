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
    driver_init,
    process_scraper_data
)
def scraper_ndrs_org(url, sobrenombre):
    driver = driver_init()
    collection, fs = connect_to_mongo()
    logger = get_logger("scraper")
    base_url = "https://www.ndrs.org.uk/"

    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    all_scraper = ""
    scraped_urls = set()
    failed_urls = set()
    object_ids = []

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

            enlace = container.select_one("a")["href"] if container.select_one("a") else None
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

                    total_links_found += 1

                    if article_full_url in scraped_urls or article_full_url in failed_urls:
                        continue

                    logger.info(f"🔗 URL encontrada: {article_full_url}")
                    driver.get(article_full_url)
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                    )

                    article_soup = BeautifulSoup(driver.page_source, "html.parser")
                    body_text = article_soup.select_one("#repbody")

                    if body_text:
                        content_text = body_text.text.strip()
                        if content_text:
                            object_id = fs.put(
                                content_text.encode("utf-8"),
                                source_url=article_full_url,
                                scraping_date=datetime.now(),
                                Etiquetas=["planta", "plaga"],
                                contenido=content_text,
                                url=url
                            )
                            object_ids.append(object_id)
                            total_scraped_successfully += 1
                            scraped_urls.add(article_full_url)
                            logger.info(f"✅ Archivo almacenado en MongoDB con object_id: {object_id}")

                            existing_versions = list(
                                fs.find({"source_url": article_full_url}).sort("scraping_date", -1)
                            )
                            if len(existing_versions) > 1:
                                oldest_version = existing_versions[-1]
                                file_id = oldest_version._id  
                                fs.delete(file_id)  
                                logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                        else:
                            total_failed_scrapes += 1
                            failed_urls.add(article_full_url)
                            logger.warning(f"⚠️ El contenido de {article_full_url} está vacío.")
                    else:
                        total_failed_scrapes += 1
                        failed_urls.add(article_full_url)
                        logger.warning(f"⚠️ No se extrajo contenido de {article_full_url}")

                driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#MainContent"))
                )
                time.sleep(3)

        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"
        
        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
    
    except Exception as e:
        logger.error(f"❌ Ocurrió un error: {e}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado")