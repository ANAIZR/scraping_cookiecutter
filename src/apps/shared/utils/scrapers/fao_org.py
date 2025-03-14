from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
from urllib.parse import urljoin
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    save_to_mongo
)


def scraper_fao_org(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"🚀 Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    urls_found = set()
    urls_scraped = set()
    urls_not_scraped = set()

    try:
        current_url = url 
        while current_url:
            driver.get(current_url)
            logger.info(f"🌐 Ingresando a la URL de FAO: {current_url}")

            soup = BeautifulSoup(driver.page_source, "html.parser")
            urls_found.add(current_url)

            h3_tags = soup.find_all("h3")
            page_text = ""

            if len(h3_tags) >= 3:
                third_h3 = h3_tags[2]
                for element in third_h3.find_all_next():
                    if element.name in ["p", "h3"]:
                        page_text += element.text.strip() + "\n"

                if page_text:
                    object_id = save_to_mongo("urls_scraper", page_text, current_url, url)
                    total_scraped_links += 1
                    urls_scraped.append(current_url)
                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                    

                else:
                    logger.warning(f"⚠️ No se extrajo contenido de {current_url}")
                    urls_not_scraped.add(current_url)

            else:
                logger.warning(
                    f"⚠️ No se encontraron los elementos esperados en {current_url}"
                )
                urls_not_scraped.add(current_url)

            next_link = soup.find("a", text="Siguiente")
            if next_link and "href" in next_link.attrs:
                current_url = urljoin(url, next_link["href"])
                logger.info(f"➡️ Navegando al siguiente enlace: {current_url}")
            else:
                logger.info(
                    "⏹️ No se encontró el enlace 'Siguiente'. Finalizando scraping."
                )
                break

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

        response = process_scraper_data(all_scraper, url, sobrenombre,collection)
        return response

    except Exception as e:
        logger.error(f"❌ Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado.")
