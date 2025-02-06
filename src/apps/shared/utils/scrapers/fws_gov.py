from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)


def scraper_fws_gov(
    url,
    sobrenombre,
):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    base_url = "https://www.fws.gov"

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.default-view"))
        )
        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")

            cards = soup.select("div.default-view mat-card")

            if cards:
                for card in cards:
                    link = card.find("a", href=True)
                    if link:
                        card_url = link["href"]
                        title = card.select_one("span")
                        all_scraper += title.text + "\n"
                        full_url = base_url + card_url
                        driver.get(full_url)

                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )

                        soup_page = BeautifulSoup(driver.page_source, "html.parser")
                        content = soup_page.select_one(
                            "div.layout-stacked-side-by-side"
                        )
                        if content:
                            all_scraper += content.get_text()
                            all_scraper += "\n\n"
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.default-view")
                            )
                        )

            try:
                next_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            ".search-pager__item",
                        )
                    )
                )
                driver.execute_script("arguments[0].click();", next_page_button)
                time.sleep(3)

            except Exception as e:

                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
