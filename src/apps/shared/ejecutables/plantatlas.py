from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import hashlib
import os
from pymongo import MongoClient
import gridfs
import time

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
fs = gridfs.GridFS(db)

def scrape_table_with_pagination(driver):
    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.select_one("#ctl00_cphBody_Grid1")
        if table:
            rows = table.select("tr")
            for row in rows:
                cols = row.find_all("td")
                if cols:
                    data = [col.text.strip() for col in cols]
                    print(f"Extracted data: {data}")
        else:
            print("Table not found on this page.")

        try:
            next_button = driver.find_element(By.ID, "ctl00_cphBody_Grid1_ctl01_ibNext")
            if next_button.is_enabled():
                next_button.click()
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_cphBody_Grid1"))
                )
            else:
                print("No more pages.")
                break
        except Exception as e:
            print(f"Error during pagination: {e}")
            break

def process_card(driver, card):
    try:
        title = card.select_one("h3").text
        link_card = card.select_one("a").get("href")
        print(f"Processing card: {title}, Link: {link_card}")
        if link_card:
            driver.get(link_card)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#aspnetForm"))
            )

            try:
                btn_selenium = driver.find_element(By.ID, "ctl00_cphHeader_ctrlHeader_btnBrowseSearch")
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(btn_selenium))
                btn_selenium.click()
                print("Button clicked. Starting table scraping...")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_cphBody_Grid1"))
                )
                scrape_table_with_pagination(driver)
            except Exception as e:
                print(f"Button not found or not clickable: {e}")
        else:
            print("No link found for this card.")
    except Exception as e:
        print(f"Error processing card: {e}")

def main():
    url = "http://www.plantatlas.usf.edu"
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(url)
    print(f"Accessing main page: {url}")

    processed_cards = set()

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "section#partners div.container"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        section = soup.select_one("section#partners div.container")
        if section:
            print("Section found. Extracting cards...")
            containers = section.select("div.partner-list")
            for container in containers:
                cards = container.select("div.col-lg-3")
                for card in cards:
                    link_card = card.select_one("a").get("href")
                    if link_card in processed_cards:
                        print(f"Card already processed: {link_card}")
                        continue

                    process_card(driver, card)
                    
                    processed_cards.add(link_card)
        else:
            print("Section not found.")
    except Exception as e:
        print(f"Error navigating main page: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
