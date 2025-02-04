from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
import random


def scraper_iucnredlist(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    visited_urls = set()
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#page"))
        )
        button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.search--site__button"))
        )
        driver.execute_script("arguments[0].click();", button)

        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.cards--narrow article")
            )
        )

        while True:
            articles = driver.find_elements(
                By.CSS_SELECTOR, "div.cards--narrow article a"
            )

            for index, article in enumerate(articles):
                href = article.get_attribute("href")

                if href in visited_urls:
                    continue

                driver.get(href)

                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                try:
                    title = ""
                    taxonomy = ""
                    habitat = ""
                    try:
                        title = WebDriverWait(driver, 30).until(
                            lambda d: d.find_element(
                                By.CSS_SELECTOR,
                                "h1.headline__title",
                            ).text.strip()
                        )
                    except Exception as e:
                        print(f"Error al obtener el título: {e}")
                    try:
                        taxonomy = WebDriverWait(driver, 30).until(
                            lambda d: d.find_element(
                                By.CSS_SELECTOR, "#taxonomy"
                            ).text.strip()
                        )
                    except Exception as e:
                        print(f"Error al obtener la taxonomia: {e}")
                    try:
                        habitat = WebDriverWait(driver, 30).until(
                            lambda d: d.find_element(
                                By.CSS_SELECTOR, "#habitat-ecology"
                            ).text.strip()
                        )
                    except Exception as e:
                        print(f"Error al obtener el hábitat: {e}")

                    text_content = title + taxonomy + habitat
                    if text_content:
                        all_scrapped += text_content
                except Exception as e:
                    print(f"Error procesando el artículo: {e}")
                visited_urls.add(href)
                time.sleep(random.randint(1, 3))
                driver.back()

            try:
                show_more_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".section__link-out"))
                )
                show_more_btn.click()

                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div.cards--narrow article")
                    )
                )
            except Exception as e:
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
