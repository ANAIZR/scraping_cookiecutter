from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
import time
from ..functions import process_scraper_data
from rest_framework.response import Response
from rest_framework import status


def initialize_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")  # Evita el uso de GPU
    options.add_argument("--no-sandbox")  # Mejora la estabilidad

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )


def connect_to_mongo():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    fs = gridfs.GridFS(db)
    return db["collection"], fs


def wait_for_element(driver, wait_time, locator):
    return WebDriverWait(driver, wait_time).until(
        EC.presence_of_element_located(locator)
    )


def scrape_table_rows(driver, wait_time, all_scraper, processed_links):
    rows = driver.find_elements(By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody tr")
    extracted_count = 0

    for row in rows:
        first_td = row.find_element(By.CSS_SELECTOR, "td a")
        link = first_td.get_attribute("href")

        if link in processed_links:
            continue

        processed_links.add(link)  
        extracted_count += 1

        driver.get(link)
        wait_for_element(
            driver, wait_time, (By.CSS_SELECTOR, "section.container div.rfInv")
        )

        cards = driver.find_elements(By.CSS_SELECTOR, "div.col-md-2")
        for card in cards:
            link_in_card = card.find_element(By.CSS_SELECTOR, "a")
            link_in_card.click()

            original_window = driver.current_window_handle
            all_windows = driver.window_handles
            new_window = [
                window for window in all_windows if window != original_window
            ][0]
            driver.switch_to.window(new_window)

            new_page_content = wait_for_element(
                driver, wait_time, (By.CSS_SELECTOR, "main.container div.parteesq")
            )
            extracted_text = new_page_content.text

            all_scraper += f"Datos extraídos de {driver.current_url}\n"
            all_scraper += extracted_text + "\n\n"
            all_scraper += "*************************"

            driver.close()
            driver.switch_to.window(original_window)

        driver.back()
        time.sleep(2)
        wait_for_element(
            driver, wait_time, (By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody")
        )

    return all_scraper, extracted_count


def get_current_page_number(driver):
    try:
        page_number_element = driver.find_element(
            By.CSS_SELECTOR, ".pagination .active a"
        )
        return int(page_number_element.text)
    except Exception:
        print("No se pudo obtener el número de página actual.")
        return None


def click_next_page(driver, wait_time):
    try:
        next_button = wait_for_element(
            driver, wait_time, (By.CSS_SELECTOR, "#DataTables_Table_0_next a")
        )
        if "disabled" in next_button.get_attribute("class"):
            print("Botón 'Siguiente' deshabilitado. No hay más páginas.")
            return False

        current_page = get_current_page_number(driver)
        next_button.click()

        WebDriverWait(driver, wait_time).until(
            lambda d: get_current_page_number(d) != current_page
        )
        wait_for_element(
            driver, wait_time, (By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody")
        )
        return True

    except:
        print(f"No se encontraron más páginas")
        return False


def scraper_aguiar_hvr(url, wait_time, sobrenombre):
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    processed_links = set()  

    try:
        driver.get(url)
        while True:
            wait_for_element(
                driver,
                wait_time,
                (By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody"),
            )

            current_page = get_current_page_number(driver)
            print(f"Procesando la página: {current_page}")

            all_scraper, extracted_count = scrape_table_rows(
                driver, wait_time, all_scraper, processed_links
            )
            print(f"Datos extraídos en la página {current_page}: {extracted_count}")

            if not click_next_page(driver, wait_time):
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
