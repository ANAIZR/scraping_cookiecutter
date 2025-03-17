from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    get_random_user_agent,
    save_to_mongo
)


def scraper_pest_alerts(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"🚀 Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    headers = {"User-Agent": get_random_user_agent()}

    urls_found = set()
    urls_scraped = set()
    urls_not_scraped = set()

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )

        while True:
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

            for row in rows:
                try:
                    second_td = row.find_elements(By.TAG_NAME, "td")[1]
                    a_tag = second_td.find_element(By.TAG_NAME, "a")
                    href = a_tag.get_attribute("href")

                    if href:
                        if href.startswith("/"):
                            href = urljoin(url, href)

                        if href not in urls_found:
                            urls_found.add(href)
                            logger.info(f"🔗 URL encontrada: {href}")

                except Exception as e:
                    logger.warning(f"⚠️ Error al extraer enlace de la fila: {e}")

            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.next"))
                )
                driver.execute_script("arguments[0].click();", next_button)
                logger.info("➡️ Cargando siguiente página...")
                time.sleep(3)
            except Exception:
                logger.info("⏹️ No hay más páginas disponibles.")
                break

        logger.info(f"🔍 Total de URLs encontradas: {len(urls_found)}")

        for link in urls_found:
            try:
                logger.info(f"🌍 Procesando URL: {link}")
                response = requests.get(link, headers=headers)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")
                content_elements = soup.select("div.bg-content-custom")

                if len(content_elements) == 2:
                    page_text = (
                        content_elements[0].get_text(separator="\n", strip=True)
                        + "\n"
                        + content_elements[1].get_text(separator="\n", strip=True)
                    )

                    object_id = save_to_mongo("urls_scraper", page_text, link, url)  # 📌 Guardar en `urls_scraper`
                    urls_scraped.add(link)
                    logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")

                    


                else:
                    logger.warning(f"⚠️ No se extrajo contenido de {link}")
                    urls_not_scraped.add(link)

            except requests.RequestException as e:
                logger.warning(f"❌ Error al acceder a {link}: {e}")
                urls_not_scraped.add(link)

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

        response = process_scraper_data(all_scraper, url, sobrenombre,"news_articles")        
        return response
     


    except Exception as e:
        logger.error(f"❌ Error durante el scraping: {e}")
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado.")
