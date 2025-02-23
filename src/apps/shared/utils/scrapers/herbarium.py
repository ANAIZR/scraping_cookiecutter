from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import time
import requests
from datetime import datetime
from bson import ObjectId
from urllib.parse import urljoin
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    load_keywords,
)

logger = get_logger("scraper")
BASE_URL = "http://www.virtualherbarium.org"

def scraper_herbarium(url, sobrenombre):
    logger.info(f"🚀 Iniciando scraping para URL: {url}")
    driver = driver_init()
    collection, fs = connect_to_mongo()
    
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    scraped_urls = [] 
    failed_urls = []
    object_ids = []

    try:
        driver.get(url)
        print(f"**** Se está scrapeando la página: {driver.current_url}")

        WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(3)

        links = driver.find_elements(By.CSS_SELECTOR, "ul.subNav li a")[:2]
        link_urls = [urljoin(BASE_URL, link.get_attribute("href")) for link in links]
        total_links_found += len(link_urls)

        for link_url in link_urls:
            print(f"🔍 Navegando a: {link_url}")
            driver.get(link_url)
            WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(3)

            # Caso 1
            if "main.php" in link_url:
                keywords = load_keywords("family.txt")
                for keyword in keywords:
                    try:
                        print(f"🔎 Buscando con palabra clave: {keyword}")

                        search_input = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='family']"))
                        )
                        search_input.clear()
                        search_input.send_keys(keyword)
                        print("✅ Palabra clave ingresada correctamente.")

                        search_input.submit()
                        print("✅ Formulario enviado correctamente.")

                        old_url = driver.current_url
                        try:
                            WebDriverWait(driver, 10).until(lambda d: d.current_url != old_url)
                        except TimeoutException:
                            print("⏳ La URL no cambió automáticamente. Intentando otra detección...")

                        time.sleep(3)

                        if len(driver.window_handles) > 1:
                            print("🆕 Se detectó una nueva pestaña. Cambiando...")
                            driver.switch_to.window(driver.window_handles[-1])

                        new_url = driver.current_url
                        print(f"✅ URL de resultados detectada: {new_url}")
                        scraped_urls.append(new_url) 

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        rows = soup.select("tbody tr")

                        if not rows:
                            print("⚠️ No se encontraron resultados en la tabla.")
                            total_failed_scrapes += 1
                            failed_urls.append(new_url)
                            continue

                        content_text = "\n".join(";".join(cell.get_text(strip=True) for cell in row.find_all("td")) for row in rows)

                        if content_text:
                            object_id = fs.put(
                                content_text.encode("utf-8"),
                                source_url=new_url,
                                scraping_date=datetime.now(),
                                Etiquetas=["planta", "plaga"],
                                contenido=content_text,
                                url=url
                            )
                            
                            existing_versions = list(
                                fs.find({"source_url": new_url}).sort("scraping_date", -1)
                            )
                            object_ids.append(object_id)
                            total_scraped_successfully += 1
                            logger.info(f"✅ Archivo almacenado en MongoDB con object_id: {object_id}")

                            if len(existing_versions) > 1:
                                oldest_version = existing_versions[-1]
                                fs.delete(oldest_version._id)  
                                logger.info(f"Se eliminó la versión más antigua con este enlace: '{new_url}' y object_id: {oldest_version['_id']}")

                    except Exception as e:
                        logger.error(f"❌ Error en búsqueda con palabra clave {keyword}: {str(e)}")
                        total_failed_scrapes += 1
                        failed_urls.append(driver.current_url)
                        continue

            # Caso 2
            elif "default.htm" in link_url:
                try:
                    submit_button = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='submit']"))
                    )
                    submit_button.click()

                    WebDriverWait(driver, 15).until(lambda d: "SearchCAYM.php" in d.current_url)
                    new_url = driver.current_url
                    print(f"✅ URL de resultados detectada: {new_url}")
                    scraped_urls.append(new_url)

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    rows = soup.select("tbody tr")
                    content_text = "\n".join(";".join(cell.get_text(strip=True) for cell in row.find_all("td")) for row in rows)

                    if content_text:
                        object_id = fs.put(
                            content_text.encode("utf-8"),
                            source_url=new_url,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=content_text,
                            url=url
                        )

                        existing_versions = list(
                            fs.find({"source_url": new_url}).sort("scraping_date", -1)
                        )
                        object_ids.append(object_id)
                        total_scraped_successfully += 1
                        logger.info(f"✅ Archivo almacenado en MongoDB con object_id: {object_id}")

                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(oldest_version._id)  
                            logger.info(f"Se eliminó la versión más antigua con este enlace: '{new_url}' y object_id: {oldest_version['_id']}")
                            

                except Exception as e:
                    logger.error(f"❌ Error en la segunda opción: {str(e)}")
                    total_failed_scrapes += 1
                    failed_urls.append(driver.current_url)
                    continue

        all_scraper = f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
    except Exception as e:
        logger.error(f"❌ Error general durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
