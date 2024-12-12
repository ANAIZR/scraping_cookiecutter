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
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status
from selenium.webdriver.common.action_chains import ActionChains


def scrape_aphidnet(
    url=None,
    wait_time=None,
    sobrenombre=None,
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
    all_scraped_fact_sheets = ""
    all_scraped_morphology = ""
    output_dir = r"C:\web_scraping_files"

    try:
        driver.get(url)

        def scraper_first():
            nonlocal all_scraped_fact_sheets
            try:
                nav_fact_sheets = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "nav.main #nav li:nth-child(4) a[href='species_list.php']",
                        )
                    )
                )
                nav_fact_sheets.click()

                content = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#content"))
                )

                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                faq_div = page_soup.select_one(".grid_8 #faq")
                h3_tags = faq_div.find_all("h3")

                for h3 in h3_tags:
                    ul_tag = h3.find_next("ul")

                    if ul_tag:
                        li_tags = ul_tag.find_all("li")

                        for li in li_tags:
                            a_tag = li.find("a", href=True)
                            if a_tag:
                                href = a_tag["href"]
                                text = a_tag.get_text(strip=True)

                                all_scraped_fact_sheets += (
                                    f"Enlace: {href}\n + {text}\n\n"
                                )

                                driver.get(url + href)
                                WebDriverWait(driver, wait_time).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "#content")
                                    )
                                )

                                page_soup = BeautifulSoup(
                                    driver.page_source, "html.parser"
                                )
                                content = page_soup.select_one("#content div.grid_12")
                                if content:
                                    hgroup = content.select_one("hgroup h1")
                                    paragraphs = content.find_all("p", limit=4)
                                    if hgroup:
                                        all_scraped_fact_sheets += (
                                            f"{hgroup.get_text()}\n"
                                        )
                                    for i, p in enumerate(paragraphs, start=1):
                                        all_scraped_fact_sheets += f"{p.get_text()}\n"

                                    all_scraped_fact_sheets += "\n\n"
                                else:
                                    print(
                                        f"No se encontró contenido para el enlace: {href}"
                                    )
            except Exception as e:
                raise Exception(f"Error al scrapear 'FACT SHEETS': {e}")

        def scraper_second():
            nonlocal all_scraped_morphology
            try:
                nav_morphology = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "nav.main #nav li:nth-child(5)")
                    )
                )

                ActionChains(driver).move_to_element(nav_morphology).perform()

                ul_tag = driver.find_element(
                    By.CSS_SELECTOR, "nav.main #nav li:nth-child(5) ul"
                )
                li_tags = ul_tag.find_elements(By.TAG_NAME, "li")
                for index, li in enumerate(li_tags):
                    if index == 0:
                        continue
                    ul_tag = driver.find_element(
                        By.CSS_SELECTOR, "nav.main #nav li:nth-child(5) ul"
                    )
                    li_tags = ul_tag.find_elements(By.CSS_SELECTOR, "li")
                    li = li_tags[index]
                    a_tag = li.find_element(By.CSS_SELECTOR, "a")
                    href = a_tag.get_attribute("href")

                    driver.get(href)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#content"))
                    )

                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    content = page_soup.select_one("section#content div.grid_8")
                    if content:
                        hgroup = content.select_one("hgroup h1")
                        paragraphs = content.find("p")
                        portfolio = page_soup.select_one(
                            "section.portfolio ul#portfolio"
                        )
                        if portfolio:
                            all_scraped_morphology += f"Enlace: {href}\n"
                            all_scraped_morphology += f"{hgroup.get_text(strip=True)}\n"
                            all_scraped_morphology += (
                                f"{paragraphs.get_text(strip=True)}\n"
                            )
                            all_scraped_morphology += (
                                f"{portfolio.get_text(strip=True)}\n\n"
                            )
            except Exception as e:
                raise Exception(f"Error al scrapear 'MORPHOLOGY': {e}")

        scraper_first()
        scraper_second()

        if all_scraped_fact_sheets.strip() and all_scraped_fact_sheets.strip():
            folder_path = generate_directory(output_dir, url)
            file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

            with open(file_path, "w", encoding="utf-8") as file:
                file.write(all_scraped_fact_sheets + all_scraped_morphology)

            with open(file_path, "rb") as file_data:
                object_id = fs.put(
                    file_data,
                    filename=os.path.basename(file_path),
                )

                data = {
                    "Objeto": object_id,
                    "Tipo": "Web",
                    "Url": url,
                    "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Etiquetas": ["planta", "plaga"],
                }
                response_data = {
                    "Tipo": "Web",
                    "Url": url,
                    "Fecha_scrapper": data["Fecha_scrapper"],
                    "Etiquetas": data["Etiquetas"],
                    "Mensaje": "Los datos han sido scrapeados correctamente.",
                }
                collection.insert_one(data)
                delete_old_documents(url, collection, fs)

            return Response(
                response_data,
                status=status.HTTP_200_OK,
            )
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
