from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    initialize_driver,
    connect_to_mongo,
    get_logger,
    process_scraper_data,
)
from rest_framework.response import Response
from rest_framework import status



def scraper_ansci_cornell(
    url,
    wait_time,
    sobrenombre,
):
    logger = get_logger("ANSCI_CORNELL", sobrenombre)

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()

    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

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

                    all_scraper += p.text + "\n"
                    

                driver.back()
                all_scraper += "**********\n"
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
                    )
                )
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response
    except Exception as e:
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
