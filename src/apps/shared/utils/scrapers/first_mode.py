from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from ..functions import process_scraper_data, connect_to_mongo, get_logger, initialize_driver
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("scraper", "first_mode")


def scraper_first_mode(
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

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
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
                            all_scraper += f"Contenido de la página {page}:\n"
                            cleaned_text = " ".join(content_container.text.split())
                            all_scraper += cleaned_text + "\n\n"

                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, content_selector)
                            )
                        )

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
