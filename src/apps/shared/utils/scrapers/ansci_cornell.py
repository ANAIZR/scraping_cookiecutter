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
import time

def scraper_ansci_cornell(url, sobrenombre):
    logger = get_logger("ANSCI_CORNELL")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    try:
        driver.get(url)
        logger.info(f"Ingresamos a la URL {url}")

        try:
            logger.info("Buscaremos el botón")
            search_li = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
                )
            )

            links = search_li.find_elements(By.TAG_NAME, "a")
            if len(links) < 2:
                logger.error("No hay suficientes enlaces dentro del li[3].")
                return Response({"message": "No hay suficientes enlaces en el menú"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            driver.execute_script("arguments[0].click();", links[0])
            logger.info("Click realizado en el primer enlace")
        except TimeoutException:
            logger.error("No encontramos el botón")
            return Response({"message": "No se encontró el botón de navegación"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        for div_index in range(10):  
            try:
                target_divs = WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
                    )
                )

                if div_index >= len(target_divs):
                    break  

                target_div = target_divs[div_index]
                links = target_div.find_elements(By.TAG_NAME, "a")
                
                for link_index in range(len(links)):
                    link = links[link_index]
                    link_href = link.get_attribute("href")
                    if not link_href:
                        continue

                    driver.get(link_href)
                    logger.info(f"Accediendo a: {link_href}")

                    page_body = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#mainContent #pagebody #main"))
                    )

                    p_tags = page_body.find_elements(By.TAG_NAME, "p")[:5]
                    all_scraper += f"URL: {link_href}\n" + "\n".join([p.text for p in p_tags]) + "\n"

                    nested_links = page_body.find_elements(By.TAG_NAME, "a")
                    for nested_link in nested_links:
                        nested_href = nested_link.get_attribute("href")
                        if nested_href:
                            driver.get(nested_href)
                            logger.info(f"Accediendo al enlace anidado: {nested_href}")

                            nested_page_body = WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "#pagebody "))
                            )
                            nested_p_tags = nested_page_body.find_elements(By.TAG_NAME, "p")[:5]
                            all_scraper += f"URL: {nested_href}\n" + "\n".join([p.text for p in nested_p_tags]) + "\n"

                            driver.back() 

                    all_scraper += "**********\n"
                    driver.back()  

                    target_divs = WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
                        )
                    )

            except StaleElementReferenceException:
                logger.warning("Se encontró un 'stale element'. Intentando refrescar los elementos...")
                driver.refresh()
                time.sleep(3) 
                continue

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
