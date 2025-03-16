from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    save_to_mongo
)


def scraper_eppo_quarentine(url, sobrenombre):
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
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.main-content div.container")
            )
        )

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        rows = soup.select("div.main-content div.container div.row")

        if len(rows) >= 4:
            fourth_row = rows[3]
            table_responsive_divs = fourth_row.select("div.table-responsive")

            for table in table_responsive_divs:
                trs = table.select("tr")

                for tr in trs:
                    tds = tr.select("td em")
                    for em in tds:
                        link_tag = em.find("a")
                        if link_tag and "href" in link_tag.attrs:
                            full_link = urljoin(url, link_tag["href"])

                            if full_link in urls_found:
                                continue  

                            urls_found.add(full_link)
                            logger.info(f"🔗 URL encontrada: {full_link}")

                            try:
                                driver.get(full_link)
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located(
                                        (
                                            By.CSS_SELECTOR,
                                            "div.col-md-6.col-sm-6.col-xs-6",
                                        )
                                    )
                                )

                                page_source_inner = driver.page_source
                                soup_inner = BeautifulSoup(
                                    page_source_inner, "html.parser"
                                )

                                content = soup_inner.select(
                                    "div.col-md-6.col-sm-6.col-xs-6"
                                )

                                if content:
                                    page_text = "\n".join(
                                        [item.get_text(strip=True) for item in content]
                                    )

                                    object_id = save_to_mongo("urls_scraper", page_text, full_link, url)
                                    total_scraped_links += 1
                                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                                    urls_scraped.add(full_link)
                                   


                            except Exception as scrape_error:
                                logger.error(
                                    f"❌ Error al procesar {full_link}: {str(scrape_error)}"
                                )
                                urls_not_scraped.add(full_link)

        all_scraper = (
            f"📌 **Reporte de scraping:**\n"
            f"🔍 URLs encontradas: {len(urls_found)}\n"
            f"✅ URLs scrapeadas: {len(urls_scraped)}\n"
            f"⚠️ URLs no scrapeadas: {len(urls_not_scraped)}\n\n"
        )

        if urls_not_scraped:
            all_scraper += (
                "⚠️ **URLs no scrapeadas:**\n" + "\n".join(urls_not_scraped) + "\n"
            )

        response = process_scraper_data(all_scraper, url, sobrenombre)        
        return response


    except Exception as e:
        logger.error(f"❌ Error en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("🛑 Navegador cerrado.")
