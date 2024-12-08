from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
import gridfs
from .functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status


def scrape_first_mode(
    url,
    search_button_selector,
    tag_name_first,
    tag_name_second,
    tag_name_third,
    attribute,
    content_selector,
    selector,
    page_principal,
    sobrenombre,
):
    # options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scrapped = ""
    try:
        driver.get(url)
        search_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, search_button_selector))
        )
        search_button.click()
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, content_selector))
        )
        page_soup = BeautifulSoup(driver.page_source, "html.parser")
        content = page_soup.select_one(content_selector)
        if content:

            tag_content = content.find_all(tag_name_first)
            for row in tag_content[1:]:
                tag_row = row.find_all(tag_name_second)
                if tag_row:
                    if tag_name_third == "href":
                        href = tag_row[0].get(tag_name_third)
                    else:
                        a_tags = tag_row[0].find(tag_name_third)
                        if a_tags:
                            href = a_tags.get(attribute)
                        else:
                            href = None
                    if href:

                        page = page_principal + href
                        if page.endswith(".pdf"):
                            continue
                        driver.get(page)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        content = BeautifulSoup(driver.page_source, "html.parser")
                        content_container = content.select_one(selector)

                        if content_container:
                            all_scrapped += f"Contenido de la página {page}:\n"
                            cleaned_text = " ".join(content_container.text.split())
                            all_scrapped += cleaned_text + "\n\n"
                        else:
                            print(f"No content found for page: {href}")
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, content_selector)
                            )
                        )

        output_dir = r"C:\web_scraping_files"
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
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
