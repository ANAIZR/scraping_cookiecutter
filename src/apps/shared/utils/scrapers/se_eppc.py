from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
from urllib.parse import urljoin
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    driver_init,
    save_to_mongo
)

def scraper_se_eppc(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"🚀 Iniciando scraping para URL: {url}")

    driver = driver_init()
    collection, fs = connect_to_mongo()

    total_urls_found = 0
    total_urls_scraped = 0
    total_non_scraped_links = 0
    all_scraper = ""
    found_urls = set()      
    scraped_urls = []       
    failed_urls = []        
    object_ids = []        

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

                        if href in found_urls:
                            continue

                        found_urls.add(href)
                        total_urls_found += 1
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
                            if href not in scraped_urls and href not in failed_urls:
                                failed_urls.append(href)
                                total_non_scraped_links += 1
                            continue

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        container = soup.select_one("div.container")

                        if container:
                            overview = container.select_one("#overview")
                            if overview:
                                page_text = overview.get_text(separator="\n", strip=True)
                                if page_text:

                                    object_id = save_to_mongo("urls_scraper", page_text, href, url)  # 📌 Guardar en `urls_scraper`
                                    total_urls_scraped += 1
                                    scraped_urls.append(url)
                                    logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")
                                    
                                else:
                                    logger.warning(f"⚠️ El contenido de #overview en {href} está vacío.")
                                    if href not in scraped_urls and href not in failed_urls:
                                        failed_urls.append(href)
                                        total_non_scraped_links += 1
                            else:
                                logger.warning(f"⚠️ No se encontró #overview dentro de div.container en {href}.")
                                if href not in scraped_urls and href not in failed_urls:
                                    failed_urls.append(href)
                                    total_non_scraped_links += 1
                        else:
                            logger.warning(f"⚠️ No se encontró 'div.container' en {href}.")
                            if href not in scraped_urls and href not in failed_urls:
                                failed_urls.append(href)
                                total_non_scraped_links += 1

            except Exception as e:
                logger.error(f"❌ Error al procesar el enlace {href}: {e}")
                if href not in scraped_urls and href not in failed_urls:
                    failed_urls.append(href)
                    total_non_scraped_links += 1

        all_scraper += f"Total enlaces encontrados: {total_urls_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_urls_scraped}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_non_scraped_links}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre,collection)
        logger.info("🚀 Scraping completado exitosamente.")
        return response

    except Exception as e:
        logger.error(f"❌ Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado.")