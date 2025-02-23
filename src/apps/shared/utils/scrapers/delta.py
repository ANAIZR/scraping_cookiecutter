from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from selenium.common.exceptions import StaleElementReferenceException
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from datetime import datetime
from bson import ObjectId

def scraper_delta(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    processed_links = set()
    base_url = "https://www.delta-intkey.com/"
    scraped_urls = []
    non_scraped_urls = []

    total_enlaces_encontrados = 0
    total_enlaces_scrapeados = 0

    try:
        driver.get(url)

        while True:
            body = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            if body:
                elementos_p = body.find_elements(By.CSS_SELECTOR, "p")
                enlaces_disponibles = False  
                for p in elementos_p:
                    try:
                        enlaces = p.find_elements(By.CSS_SELECTOR, "a")
                        if enlaces:
                            for enlace in enlaces:
                                href = enlace.get_attribute("href")
                                if (
                                    href
                                    and href.startswith(f"{base_url}")
                                    and href not in processed_links
                                ):
                                    enlaces_disponibles = True
                                    processed_links.add(href)
                                    total_enlaces_encontrados += 1
                                    driver.get(href)

                                    try:
                                        body_url = WebDriverWait(driver, 30).until(
                                            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                                        )
                                    except Exception as e:
                                        non_scraped_urls.append(href)
                                        driver.back()
                                        continue

                                    if body_url:
                                        content_text = body_url.text.strip()
                                        if content_text:
                                            object_id = fs.put(
                                                content_text.encode("utf-8"),
                                                source_url=href,
                                                scraping_date=datetime.now(),
                                                Etiquetas=["planta", "plaga"],
                                                contenido=content_text,
                                                url=url
                                            )
                                            total_enlaces_scrapeados += 1
                                            scraped_urls.append(href)
                                            logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                            existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))

                                            if len(existing_versions) > 1:
                                                oldest_version = existing_versions[-1]
                                                fs.delete(oldest_version._id)  
                                                logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")

                                            


                                        elementos_p_url = body_url.find_elements(By.CSS_SELECTOR, "p")
                                        for p_url in elementos_p_url:
                                            try:
                                                enlaces_url = p_url.find_elements(By.CSS_SELECTOR, "a")
                                                if enlaces_url:
                                                    for enlace_url in enlaces_url:
                                                        href_url = enlace_url.get_attribute("href")
                                                        if (
                                                            href_url
                                                            and href_url.startswith(f"{base_url}")
                                                            and href_url.endswith(".htm")
                                                            and href_url not in processed_links
                                                        ):
                                                            processed_links.add(href_url)
                                                            total_enlaces_encontrados += 1
                                                            driver.get(href_url)

                                                            try:
                                                                body = WebDriverWait(driver, 30).until(
                                                                    EC.presence_of_element_located(
                                                                        (By.CSS_SELECTOR, "body")
                                                                    )
                                                                )
                                                                if body:
                                                                    total_enlaces_scrapeados += 1
                                                                    scraped_urls.append(href_url)
                                                                    content_text = body.text.strip()
                                                                    if content_text:
                                                                        object_id = fs.put(
                                                                            content_text.encode("utf-8"),
                                                                            source_url=href_url,
                                                                            scraping_date=datetime.now(),
                                                                            Etiquetas=["planta", "plaga"],
                                                                            contenido=content_text,
                                                                            url=url
                                                                        )
                                                                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                                                        existing_versions = list(fs.find({"source_url": href_url}).sort("scraping_date", -1))

                                                                        if len(existing_versions) > 1:
                                                                            oldest_version = existing_versions[-1]
                                                                            fs.delete(oldest_version._id)  
                                                                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")

                                                                        

                                                            except Exception as e:
                                                                print(f"Error cargando {href_url}: {e}")
                                                            driver.back()
                                            except Exception as e:
                                                print(f"Error al procesar sub enlace: {e}")
                                                continue

                                    driver.back()
                                    body = WebDriverWait(driver, 30).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                                    )
                                    break
                    except StaleElementReferenceException:
                        continue
                    except Exception as e:
                        non_scraped_urls.append(href)
                        continue

                if not enlaces_disponibles:
                    break

        all_scraper += (
            f"Total de enlaces encontrados: {total_enlaces_encontrados}\n"
            f"Total de enlaces scrapeados: {total_enlaces_scrapeados}\n"
            f"Enlaces scrapeados:\n" + "\n".join(scraped_urls) + "\n"
            f"Enlaces no scrapeados:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        try:
            driver.quit()
        except Exception as e:
            logger.error(f"Error al cerrar el navegador: {e}")
