from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    save_to_mongo
)


def clean_text(text):
    return " ".join(text.split()).strip()


def format_scraper_data_with_headers(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    formatted_text = ""
    for element in soup.find_all(recursive=False):
        if element.name == "b":
            formatted_text += f"\n{element.get_text()}\n"
        elif element.get_text(strip=True):
            formatted_text += f"{element.get_text(separator=' ')} "
    return formatted_text.strip()


def scraper_species(driver, lookupid):
    base_url = "https://diaspididae.linnaeus.naturalis.nl/linnaeus_ng/app/views/species/taxon.php"
    full_url = f"{base_url}?id={lookupid}"

    try:
        driver.get(full_url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#content.taxon-detail"))
        )
        content_div = driver.find_element(By.CSS_SELECTOR, "div#content.taxon-detail")
        html_content = content_div.get_attribute("innerHTML")

        soup = BeautifulSoup(html_content, "html.parser")
        scraped_text = format_scraper_data_with_headers(html_content)

        return {
            "url": full_url,
            "text": scraped_text,
        }
    except Exception as e:
        return None


def scraper_diaspididae(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"🚀 Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    urls_found = set()
    urls_scraped = set()
    urls_not_scraped = set()

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "p.row"))
        )
        elements = driver.find_elements(By.CSS_SELECTOR, "p.row")
        lookup_ids = [el.get_attribute("lookupid") for el in elements]

        for lookupid in lookup_ids:
            scraped_data = scraper_species(driver, lookupid)

            if scraped_data:
                full_url = scraped_data["url"]
                urls_found.add(full_url)
                logger.info(f"🔗 URL encontrada: {full_url}")

                if scraped_data["text"]:
                    object_id = save_to_mongo(
                        collection_name="urls_scraper",
                        content_text=scraped_data["text"],
                        href=full_url,
                        url=url
                    )

                    if object_id:
                        urls_scraped.add(full_url)
                        logger.info(f"✅ Contenido almacenado en MongoDB con ID: {object_id}")


                else:
                    urls_not_scraped.add(full_url)
                    logger.warning(f"⚠️ No se extrajo contenido de {full_url}")

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
            all_scraper += "⚠️ **URLs no scrapeadas:**\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre,collection)
        return response

    except Exception as e:
        logger.error(f"❌ Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado.")
