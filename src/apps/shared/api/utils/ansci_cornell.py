from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import gridfs
from .functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status


def scrape_ansci_cornell(
    url,
    wait_time,
    sobrenombre,
):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scrapped = ""
    output_dir = r"C:\web_scraping_files"

    try:
        driver.get(url)
        search_button = (
            WebDriverWait(driver, wait_time)
            .until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
                )
            )
            .find_elements(By.TAG_NAME, "a")[1]
        )
        search_button.click()

        target_divs = WebDriverWait(driver, wait_time).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
            )
        )
        for div_index, target_div in enumerate(target_divs, start=1):
            urls = target_div.find_elements(By.TAG_NAME, "a")
            for link_index, link in enumerate(urls, start=1):
                link_href = link.get_attribute("href")
                driver.get(link_href)
                pageBody = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#mainContent #pagebody #main")
                    )
                )
                p_tags = pageBody.find_elements(By.TAG_NAME, "p")[:5]

                for i, p in enumerate(p_tags, start=1):

                    all_scrapped += p.text + "\n"

                driver.back()

                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
                    )
                )
        if all_scrapped.strip():
            response_data = save_scraped_data(
                all_scrapped, url, sobrenombre, output_dir, collection, fs
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
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
