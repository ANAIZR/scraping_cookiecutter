from urllib.parse import urljoin
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from ..functions import (
    initialize_driver,
    process_scraper_data,
    connect_to_mongo,
    get_random_user_agent,
    get_logger,
    save_to_mongo
)
from rest_framework.response import Response
from rest_framework import status

total_scraped_links = 0
scraped_urls = []
non_scraped_urls = []

url_padre = ""
urls_to_scrape = []
fs = None
headers = None
logger = get_logger("scraper")

def extract_text(current_url):
    global total_scraped_links
    try:
        response = requests.get(current_url, headers=headers)
        response.raise_for_status()
        print(f"Procesando URL by quma: {current_url}")

        soup = BeautifulSoup(response.content, "html.parser")
        table_element = soup.find("table", class_="datagrid")

        if table_element:
            trs = table_element.select("tr")
            
            body_text = ""
            for tr in trs:
                tds = tr.select("td")
                for td in tds:
                    body_text += f"{td.get_text(strip=True)}  "
                body_text += ";\n"

            if body_text:
                object_id = save_to_mongo("urls_scraper", body_text, current_url, url_padre)  # 📌 Guardar en `urls_scraper`
                total_scraped_links += 1
                scraped_urls.append(current_url)
                logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")
                
            else:
                non_scraped_urls.append(current_url)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error al procesar la URL {current_url}: {e}")


def get_soup(driver, url):
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "section#partners div.container")
        )
    )
    return BeautifulSoup(driver.page_source, "html.parser")


def process_cards(driver, soup, processed_cards):
    all_scraper_page = []

    containers = soup.select("div.partner-list")
    for container in containers:
        cards = container.select("div.col-lg-3")
        cards = cards[1:]
        for card in cards:
            try:
                link_card = card.select_one("h3 > a")
                if not link_card:
                    continue
                link_card = link_card.get("href")
                if link_card in processed_cards:
                    continue

                title = card.select_one("h3").text
                print(f"Processing card: {title}, Link: {link_card}")
                if link_card:
                    all_scraper_page.extend(scraper_card_page(driver, link_card))
                processed_cards.add(link_card)

            except Exception as e:
                print(f"Error processing card: {e}")

    return all_scraper_page

def scrape_pages_in_parallel(url_list):
    print("Scraping pages in parallel")
    global non_scraped_urls
    new_links = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_url = {
            executor.submit(extract_text, url): (url)
            for url in url_list
        }
        for future in as_completed(future_to_url):
            try:
                result_links = future.result()
                new_links.extend(result_links)
            except Exception as e:
                logger.error(f"Error en tarea de scraping: {str(e)}")
                non_scraped_urls += 1
    return new_links

def scraper_card_page(driver, link_card):
    driver.get(link_card)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#aspnetForm"))
    )

    try:
        btn_selenium = driver.find_element(
            By.ID, "ctl00_cphHeader_ctrlHeader_btnBrowseSearch"
        )
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(btn_selenium))
        btn_selenium.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_cphBody_Grid1"))
        )

        all_scraper_page = []
        number_page = 1
        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.select_one("#ctl00_cphBody_Grid1")
            if table:
                rows = table.select("tr.altrow")
                for row in rows:
                    col = row.select_one("td.wideText")
                    if col:
                        link_tag = col.select_one("em a")
                        if link_tag and link_tag.has_attr("href"):
                            link = link_tag["href"]
                            href = urljoin(link_card, link)
                            print("href by quma: ", href)
                            urls_to_scrape.append(href)

            try:
                next_button = driver.find_element(
                    By.ID, "ctl00_cphBody_Grid1_ctl01_ibNext"
                )
                if next_button.is_enabled():
                    number_page += 1
                    next_button.click()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "#ctl00_cphBody_Grid1")
                        )
                    )
                else:
                    break
            except Exception as e:
                print(f"Error during pagination: {e}")
                break

        urls_scrappeds = scrape_pages_in_parallel(urls_to_scrape)

        return all_scraper_page
    except Exception as e:
        print(f"Error processing card page: {e}")
        return []

def scraper_plant_atlas(url, sobrenombre):
    global url_padre,headers,fs,total_scraped_links,scraped_urls,non_scraped_urls
    url_padre = url
    driver = None


    collection, fs = connect_to_mongo()
    headers = {"User-Agent": get_random_user_agent()}
    all_scraper = ""

    try:
        driver = initialize_driver()
        soup = get_soup(driver, url)

        processed_cards = set()
        all_scraper_page = process_cards(driver, soup, processed_cards)

        all_scraper = (
            f"Total enlaces scrapeados: {total_scraped_links}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)        
        return response
     


    except Exception as e:
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        if driver:
            driver.quit()
