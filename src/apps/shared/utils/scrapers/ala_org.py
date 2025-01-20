from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import gridfs
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_ala_org(
    url,
    sobrenombre,
):
    logger = get_logger("ALA_ORG",sobrenombre)

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")


    all_scraper = ""
    try:
        driver.get(url)
        btn = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']"))
        )
        btn.click()
        time.sleep(2)

        while True:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ol"))
            )

            lis = driver.find_elements(By.CSS_SELECTOR, "ol li.search-result")

            for li in lis:
                try:
                    a_tag = li.find_element(By.CSS_SELECTOR, "a")
                    href = a_tag.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            href = url + href[1:]

                        a_tag.click()

                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "section.container-fluid")
                            )
                        )

                        content = driver.find_element(
                            By.CSS_SELECTOR, "section.container-fluid"
                        )
                        all_scraper += content.text

                        driver.back()

                        time.sleep(2)

                except Exception as e:
                    print(
                        f"No se pudo hacer clic en el enlace o error al procesar el <li>: {e}"
                    )

            try:
                next_page_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")
                next_page_url = next_page_btn.get_attribute("href")
                if next_page_url:
                    driver.get(next_page_url)
                    time.sleep(3)
                else:
                    break
            except Exception as e:
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response
    finally:
        driver.quit()
