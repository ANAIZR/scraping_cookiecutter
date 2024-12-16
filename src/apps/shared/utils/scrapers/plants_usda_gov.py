from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
from ..functions import save_scraper_data
from rest_framework.response import Response
from rest_framework import status
import time
from bs4 import BeautifulSoup


def scraper_plants_usda_gov(
    url,
    sobrenombre,
):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    all_scraper = ""

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#main-content"))
        )

        characteristic = driver.find_element(
            By.CSS_SELECTOR, "div.sidebar-desktop li:first-child a"
        )
        characteristic.click()

        time.sleep(2)

        while True:
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "section.content table tbody tr")
                    )
                )

                soup = BeautifulSoup(driver.page_source, "html.parser")
                tr_tags = soup.select("section.content table tbody tr")
                time.sleep(2)

                for index, tr in enumerate(tr_tags[1:], start=1):
                    try:
                        if tr.select("td"):
                            link_tag = tr.select_one("td:nth-child(2) a")
                            if link_tag:
                                href = link_tag.get("href")
                                if href.startswith("/"):
                                    href = f"https://plants.usda.gov{href}"
                                    driver.get(href)

                                    WebDriverWait(driver, 60).until(
                                        EC.visibility_of_element_located(
                                            (
                                                By.CSS_SELECTOR,
                                                "table.usa-table.width-full.classification-table",
                                            )
                                        )
                                    )
                                    page_soup = BeautifulSoup(
                                        driver.page_source, "html.parser"
                                    )

                                    select_element = page_soup.find(
                                        "table",
                                        class_="usa-table width-full classification-table",
                                    )
                                    if select_element:
                                        all_scraper += select_element.text.strip()

                                    driver.back()
                                    WebDriverWait(driver, 30).until(
                                        EC.presence_of_all_elements_located(
                                            (
                                                By.CSS_SELECTOR,
                                                "section.content table tbody tr",
                                            )
                                        )
                                    )

                    except Exception as e:
                        import traceback

                        traceback.print_exc()

                try:
                    next_page_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (
                                By.CSS_SELECTOR,
                                "li.usa-pagination__item.usa-pagination__arrow a.usa-pagination__next-page",
                            )
                        )
                    )
                    driver.execute_script("arguments[0].click();", next_page_button)
                    time.sleep(3)
                except Exception as e:
                    break

            except Exception as e:
                break

        if all_scraper.strip():
            response_data = save_scraper_data(
                all_scraper, url, sobrenombre, collection, fs
            )

            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos para scrapear.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
