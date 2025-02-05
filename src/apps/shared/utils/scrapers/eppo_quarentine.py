from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup  
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_eppo_quarentine(url, sobrenombre):
    logger = get_logger("scraper")

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.main-content div.container"))
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
                            link = link_tag["href"]
                            full_link = urljoin(url, link)  

                            logger.info(f"Accediendo a: {full_link}")
                            driver.get(full_link)

                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "div.col-md-6.col-sm-6.col-xs-6"))
                            )

                            page_source_inner = driver.page_source
                            soup_inner = BeautifulSoup(page_source_inner, "html.parser")

                            content = soup_inner.select("div.col-md-6.col-sm-6.col-xs-6")

                            if content:
                                page_text = "\n".join([item.get_text(strip=True) for item in content])
                                all_scraper += f"\n\nURL: {full_link}\n{page_text}\n"

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
