from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    get_random_user_agent,
)
from datetime import datetime

def scraper_pest_report(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    headers = {"User-Agent": get_random_user_agent()}
    non_scraped_urls = []
    scraped_urls = []

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )

        all_links = set()

        while True:
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

            for row in rows:
                try:
                    second_td = row.find_elements(By.TAG_NAME, "td")[1]
                    a_tag = second_td.find_element(By.TAG_NAME, "a")
                    href = a_tag.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            href = url + href[1:]
                        all_links.add(href)
                except Exception as e:
                    logger.warning(f"Error al extraer enlace de la fila: {e}")

            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.next"))
                )
                next_button.click()
                time.sleep(3)
            except Exception:
                break

        all_scraper += f"Total de enlaces extraídos: {len(all_links)}"

        for link in all_links:
            try:
                logger.info(f"Procesando URL: {link}")
                response = requests.get(link, headers=headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")

                content_elements = soup.select("div.bg-content-custom")
                if len(content_elements) == 2:
                    content = (
                        content_elements[0].get_text(separator="\n", strip=True)
                        + "\n"
                        + content_elements[1].get_text(separator="\n", strip=True)
                    )
                    # all_scraper += f"URL: {link}\n{content}\n{'-'*80}\n\n"
                    if content:
                        object_id = fs.put(
                            content.encode("utf-8"),
                            source_url=link,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=content,
                            url=url
                        )
                        scraped_urls.append(link)
                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                        existing_versions = list(fs.find({"source_url": link}).sort("scraping_date", -1))
                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            file_id = oldest_version._id  # Esto obtiene el ID correcto
                            fs.delete(file_id)  # Eliminar la versión más antigua
                            logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                    else:
                        non_scraped_urls.append(link)

            except requests.RequestException as e:
                logger.warning(f"Error al acceder a {link}: {e}")

        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
