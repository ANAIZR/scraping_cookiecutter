from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from ..functions import (
    initialize_driver,
    save_scraper_data,
    connect_to_mongo,
    get_logger
)
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("scraper_plant_atlas")


def get_soup(driver, url):
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "section#partners div.container"))
    )
    return BeautifulSoup(driver.page_source, "html.parser")


def process_cards(driver, soup, processed_cards):
    all_scraper_page = []
    containers = soup.select("div.partner-list")
    
    for container in containers:
        cards = container.select("div.col-lg-3")
        for card in cards:
            try:
                link_card = card.select_one("a")
                if not link_card:
                    continue

                link_card = link_card.get("href")
                if link_card in processed_cards:
                    continue

                title = card.select_one("h3").text.strip()
                logger.info(f"Processing card: {title}, Link: {link_card}")

                if link_card:
                    all_scraper_page.extend(scraper_card_page(driver, link_card))

                processed_cards.add(link_card)

            except Exception as e:
                logger.error(f"Error processing card: {e}")

    return all_scraper_page


def scraper_card_page(driver, link_card):
    driver.get(link_card)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#aspnetForm"))
        )

        try:
            btn_selenium = driver.find_element(By.ID, "ctl00_cphHeader_ctrlHeader_btnBrowseSearch")
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable(btn_selenium))
            btn_selenium.click()
        except Exception:
            logger.warning("Botón de búsqueda no encontrado o no clickeable. Continuando...")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_cphBody_Grid1"))
        )

        all_scraper_page = []
        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.select_one("#ctl00_cphBody_Grid1")
            
            if table:
                rows = table.select("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if cols:
                        data = [col.text.strip() for col in cols]
                        all_scraper_page.append(data)

            try:
                next_button = driver.find_element(By.ID, "ctl00_cphBody_Grid1_ctl01_ibNext")
                
                if next_button.is_displayed() and next_button.is_enabled():
                    next_button.click()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_cphBody_Grid1"))
                    )
                else:
                    logger.info("No hay más páginas disponibles.")
                    break
            except Exception:
                logger.info("No se encontró el botón de siguiente página o no es clickeable.")
                break

        return all_scraper_page
    except Exception as e:
        logger.error(f"Error processing card page: {e}")
        return []


def scraper_plant_atlas(url, sobrenombre):
    all_scraper = ""
    driver = initialize_driver()

    try:
        collection, fs = connect_to_mongo()
        soup = get_soup(driver, url)

        processed_cards = set()
        all_scraper_page = process_cards(driver, soup, processed_cards)

        all_scraper = "\n".join([", ".join(row) for row in all_scraper_page])

        data = save_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return data

    except Exception as e:
        logger.error(f"Error en el scraper: {e}")
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        if driver:
            driver.quit()
