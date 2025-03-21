from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    save_to_mongo,
    load_keywords
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import time
from bs4 import BeautifulSoup
from datetime import datetime

logger = get_logger("scraper")
non_scraped_urls = []  
scraped_urls = []
total_scraped_links = 0



def scraper_catalogue_of_life(url, sobrenombre):
    global total_scraped_links
    logger.info(f"🚀 Iniciando scraping para URL: {url}")
    driver = driver_init()
    collection, fs = connect_to_mongo()

    keywords = load_keywords("plants.txt")
    all_scraper = ""

    try:
        driver.get(url)
        logger.info("✅ Página cargada exitosamente.")

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "search_string"))
        )
        logger.info("🔎 Barra de búsqueda localizada.")

        for index, keyword in enumerate(keywords):
            logger.info(f"🔍 Buscando la palabra clave: {keyword}")
            all_scraper += f"Palabra clave {index + 1}: {keyword}\n"
            random_wait()

            search_box.clear()
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )
            logger.info(f"📄 Resultados cargados para: {keyword}")

            rows = driver.find_elements(By.XPATH, "//tr[starts-with(@id, 'record_')]")
            for index in range(len(rows)):
                rows = driver.find_elements(By.XPATH, "//tr[starts-with(@id, 'record_')]")
                row = rows[index]
                record_id = row.get_attribute("id")
                logger.info(f"📌 Procesando fila con id: {record_id}")

                try:
                    next_row = row.find_element(By.XPATH, "following-sibling::tr")
                    first_td = next_row.find_element(By.TAG_NAME, "td")
                    link = first_td.find_element(By.TAG_NAME, "a")
                    if link and link.get_attribute("href"):
                        href = link.get_attribute("href")
                        logger.info(f"🌐 Accediendo al enlace: {href}")
                        driver.get(href)
                        all_scraper += f"🔗 Link: {href}\n"
                        
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                        )

                        page_content = BeautifulSoup(driver.page_source, "html.parser")
                        td_element = page_content.select(
                            'div table:nth-child(1) tr:nth-child(1) td:nth-child(3)[valign="top"]'
                        )
                        if td_element:
                            cleaned_text = " ".join(td_element[0].get_text().split())
                            
                            if cleaned_text:
                                object_id = save_to_mongo("urls_scraper", cleaned_text, href, url)  # 📌 Guardar en `urls_scraper`
                                total_scraped_links += 1
                                scraped_urls.append(href)
                                logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")

                            else:
                                non_scraped_urls.append(href)
                        else:
                            logger.warning(f"⚠️ No se encontró contenido válido en {href}")
                        
                        all_scraper += "\n\n******************\n\n"
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                        )

                        random_wait()

                except Exception as e:
                    logger.error(f"❌ Error procesando el enlace en la fila con id {record_id}: {str(e)}")

            driver.get(url)
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "search_string"))
            )
            logger.info("🔄 Regresando a la página principal para la siguiente búsqueda.")

        all_scraper = (
            f"📌 **Resumen del scraping:**\n"
            f"✅ Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"🔗 URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"⚠️ Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"❌ URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)        
        return response


    except Exception as e:
        logger.error(f"❌ Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado.")

def random_wait(min_wait=2, max_wait=6):
    wait_time = random.uniform(min_wait, max_wait)
    logger.info(f"⏳ Esperando {wait_time:.2f} segundos...")
    time.sleep(wait_time)
