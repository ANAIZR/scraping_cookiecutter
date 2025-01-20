from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)


def scraper_pest_alerts(
    url,
    sobrenombre,
):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
        )

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        original_window = driver.current_window_handle

        for row in rows:
            try:
                second_td = row.find_elements(By.TAG_NAME, "td")[1]
                a_tag = second_td.find_element(By.TAG_NAME, "a")
                href = a_tag.get_attribute("href")
                if href:
                    if href.startswith("/"):
                        href = url + href[1:]
                    driver.execute_script("window.open(arguments[0]);", href)

                    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

                    new_window = driver.window_handles[1]
                    driver.switch_to.window(new_window)

                    WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "div.bg-content-custom")
                        )
                    )

                    content_elements = driver.find_elements(
                        By.CSS_SELECTOR, "div.bg-content-custom"
                    )
                    if len(content_elements) == 2:
                        content = (
                            content_elements[0].text + "\n" + content_elements[1].text
                        )
                        all_scraper += content

                    driver.close()

                    driver.switch_to.window(original_window)

                    time.sleep(2)

            except Exception as e:
                print(f"Error al procesar la fila o hacer clic en el enlace: {e}")
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
