from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from ..functions import (
    initialize_driver,
    connect_to_mongo,
    get_logger,
    process_scraper_data,
)
from rest_framework.response import Response
from rest_framework import status

def scraper_ansci_cornell(url, sobrenombre):
    logger = get_logger("ANSCI_CORNELL")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    try:
        driver.get(url)
        logger.info(f"Ingresamos a la URL {url}")

        target_divs = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
            )
        )
        num_divs = len(target_divs)
        logger.info(f"Encontrados {num_divs} divs para procesar")

        for div_index in range(num_divs):
            target_divs = WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
                )
            )
            target_div = target_divs[div_index]

            links = target_div.find_elements(By.TAG_NAME, "a")
            logger.info(f"Div {div_index + 1}/{num_divs}: Encontrados {len(links)} enlaces")

            # Recorrer todos los enlaces dentro del div
            for link_index, link in enumerate(links, start=1):
                link_href = link.get_attribute("href")
                if not link_href:
                    continue  

                logger.info(f"Accediendo al enlace {link_index} en el div {div_index + 1}: {link_href}")
                driver.get(link_href)

                page_body = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,  "#pagebody"))
                )

                p_tags = page_body.find_elements(By.TAG_NAME, "p")[:5]
                for p_index, p in enumerate(p_tags, start=1):
                    all_scraper += f"URL: {link_href}\nPárrafo {p_index}: {p.text}\n"

                nested_links = page_body.find_elements(By.TAG_NAME, "a")
                for nested_link_index, nested_link in enumerate(nested_links, start=1):
                    nested_href = nested_link.get_attribute("href")
                    if nested_href:
                        logger.info(f"Accediendo al enlace anidado {nested_link_index}: {nested_href}")
                        driver.get(nested_href)

                        nested_page_body = WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "#pagebody"))
                        )
                        nested_p_tags = nested_page_body.find_elements(By.TAG_NAME, "p")[:5]
                        for nested_p in nested_p_tags:
                            all_scraper += f"URL: {nested_href}\n{nested_p.text}\n"

                        driver.back()

                driver.back()

                target_divs = WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
                    )
                )
                target_div = target_divs[div_index]
                links = target_div.find_elements(By.TAG_NAME, "a")

            logger.info(f"Finalizado div {div_index + 1}/{num_divs}")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        driver.quit()
