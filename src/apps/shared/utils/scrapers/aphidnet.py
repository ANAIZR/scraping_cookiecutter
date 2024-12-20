from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status
from selenium.webdriver.common.action_chains import ActionChains

logger = get_logger("scraper")


def scraper_aphidnet(
    url=None,
    wait_time=None,
    sobrenombre=None,
):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()

    collection, fs = connect_to_mongo("scrapping-can", "collection")

    all_scraper_fact_sheets = ""
    all_scraper_morphology = ""

    total_li_captured = 0
    total_li_scraped = 0

    # output_dir = os.path.expanduser("~/")
    output_dir = r"C:\web_scraper_files"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        driver.get(url)

        def scraper_first():
            nonlocal all_scraper_fact_sheets, total_li_captured, total_li_scraped
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
                        total_li_captured += len(li_tags)

                        for li in li_tags:
                            a_tag = li.find("a", href=True)
                            if a_tag:
                                href = a_tag["href"]
                                text = a_tag.get_text(strip=True)
                                total_li_scraped += 1

                                all_scraper_fact_sheets += (
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
                                        all_scraper_fact_sheets += (
                                            f"{hgroup.get_text()}\n"
                                        )
                                    for i, p in enumerate(paragraphs, start=1):
                                        all_scraper_fact_sheets += f"{p.get_text()}\n"

                                    all_scraper_fact_sheets += "\n\n"
                                else:
                                    logger.warning(
                                        f"No se encontró contenido para el enlace: {href}"
                                    )
            except Exception as e:
                logger.error(f"Error al scrapear 'FACT SHEETS': {e}")
                raise Exception(f"Error al scrapear 'FACT SHEETS': {e}")

        def scraper_second():
            nonlocal all_scraper_morphology, total_li_captured, total_li_scraped
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
                total_li_captured += len(li_tags)

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

                    total_li_scraped += 1

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
                            all_scraper_morphology += f"Enlace: {href}\n"
                            all_scraper_morphology += f"{hgroup.get_text(strip=True)}\n"
                            all_scraper_morphology += (
                                f"{paragraphs.get_text(strip=True)}\n"
                            )
                            all_scraper_morphology += (
                                f"{portfolio.get_text(strip=True)}\n\n"
                            )
            except Exception as e:
                logger.error(f"Error al scrapear 'MORPHOLOGY': {e}")
                raise Exception(f"Error al scrapear 'MORPHOLOGY': {e}")

        scraper_first()
        scraper_second()
        all_scraper = (
            (all_scraper_fact_sheets.strip() + " " + all_scraper_morphology.strip())
            if all_scraper_fact_sheets.strip() and all_scraper_morphology.strip()
            else ""
        )

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response
    except Exception as e:
        logger.error(f"Error general: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
