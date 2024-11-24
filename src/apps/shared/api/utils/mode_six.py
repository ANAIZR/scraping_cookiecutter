from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import gridfs
import os
from ..utils.functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status
from selenium.webdriver.common.action_chains import ActionChains


def scrape_mode_sixth(
    url=None,
    wait_time=None,
    sobrenombre=None,
    search_button_selector=None,
    search_button_selector_second=None,
    content_selector=None,
    content_selector_second=None,
    content_selector_third=None,
    content_selector_fourth=None,
    content_selector_fifth=None,
    tag_name_first=None,
    tag_name_second=None,
    tag_name_third=None,
    tag_name_fourth=None,
    tag_name_fifth=None,
    tag_name_sixth=None,
    attribute=None,
    title=None,
):
    # options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scraped_fact_sheets = ""
    all_scraped_morphology = ""

    try:
        driver.get(url)
        def scraper_first():
            nonlocal all_scraped_fact_sheets  
            print(f"all_scraped_fact_sheets antes de modificar: {all_scraped_fact_sheets}")

            try:
                nav_fact_sheets = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, search_button_selector)
                    )
                )
                nav_fact_sheets.click()

                content = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, content_selector))
                )

                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                faq_div = page_soup.select_one(tag_name_first)
                h3_tags = faq_div.find_all(tag_name_second)

                for h3 in h3_tags:
                    ul_tag = h3.find_next(tag_name_third)

                    if ul_tag:
                        li_tags = ul_tag.find_all(tag_name_fourth)

                        for li in li_tags:
                            a_tag = li.find(tag_name_fifth, href=True)
                            if a_tag:
                                href = a_tag[attribute]
                                text = a_tag.get_text(strip=True)

                                all_scraped_fact_sheets += f"Enlace: {href}\n + {text}\n\n"

                                driver.get(url + href)
                                WebDriverWait(driver, wait_time).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, content_selector))
                                )

                                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                                content = page_soup.select_one(content_selector_second)
                                if content:
                                    hgroup = content.select_one(title)
                                    paragraphs = content.find_all(tag_name_sixth, limit=4)
                                    if hgroup:
                                        all_scraped_fact_sheets += f"{hgroup.get_text()}\n"
                                    for i, p in enumerate(paragraphs, start=1):
                                        all_scraped_fact_sheets += f"{p.get_text()}\n"

                                    all_scraped_fact_sheets += "\n\n"
                                else:
                                    print(f"No se encontró contenido para el enlace: {href}")
            except Exception as e:
                print(f"Error procesando un elemento: {e}")

        def scraper_second():
            nonlocal all_scraped_morphology
            nav_morphology = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, search_button_selector_second)
                )
            )

            ActionChains(driver).move_to_element(nav_morphology).perform()

            ul_tag = driver.find_element(By.CSS_SELECTOR, content_selector_third)
            li_tags = ul_tag.find_elements(By.TAG_NAME, tag_name_fourth)
            print(f"Total de li_tags encontrados: {len(li_tags)}")

            for index, li in enumerate(li_tags):
                try:
                    if index == 0:
                        continue
                    ul_tag = driver.find_element(
                        By.CSS_SELECTOR, content_selector_third
                    )
                    li_tags = ul_tag.find_elements(By.CSS_SELECTOR, tag_name_fourth)
                    li = li_tags[index]
                    a_tag = li.find_element(By.CSS_SELECTOR, tag_name_fifth)

                    href = a_tag.get_attribute(attribute)

                    driver.get(href)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, content_selector)
                        )
                    )

                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    content = page_soup.select_one(content_selector_fourth)
                    if content:
                        hgroup = content.select_one(title)
                        paragraphs = content.find(tag_name_sixth)
                        portfolio = page_soup.select_one(content_selector_fifth)
                        all_scraped_morphology = f"Enlace: {href}\n"
                        if portfolio:
                            print("portfolio", portfolio)

                            all_scraped_morphology += f"{hgroup.get_text()}\n"
                            all_scraped_morphology += (
                                f"{paragraphs.get_text(strip=True)}\n"
                            )
                            all_scraped_morphology += f"{portfolio.get_text()}\n\n"

                except Exception as e:
                    print(f"Error procesando un elemento: {e}")

        scraper_first()
        scraper_second()

        output_dir = r"C:\web_scraping_files"
        folder_path = generate_directory(output_dir, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(all_scraped_fact_sheets + all_scraped_morphology)

        with open(file_path, "rb") as file_data:
            object_id = fs.put(file_data, filename=os.path.basename(file_path))

            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }

            collection.insert_one(data)
            delete_old_documents(url, collection, fs)
        return Response(
            {"message": "Scraping completado y datos guardados en MongoDB."},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
