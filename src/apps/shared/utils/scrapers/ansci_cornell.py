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
    collection, fs = connect_to_mongo()
    all_scraper = ""
    visited_urls = set()  

    try:
        driver.get(url)

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

        target_divs = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
            )
        )
        num_divs = len(target_divs)

        for div_index in range(num_divs):
            for retry in range(3):  
                try:
                    target_divs = WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
                        )
                    )
                    target_div = target_divs[div_index]

                    links = target_div.find_elements(By.TAG_NAME, "a")

                    link_index = 0
                    while link_index < len(links):  
                        try:
                            links = target_div.find_elements(By.TAG_NAME, "a") 
                            link = links[link_index]
                            link_href = link.get_attribute("href")

                            if not link_href or link_href in visited_urls:
                                link_index += 1
                                continue  

                            visited_urls.add(link_href)  
                            driver.get(link_href)

                            page_body = WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "#pagebody"))
                            )

                            p_tags = page_body.find_elements(By.TAG_NAME, "p")[:5]
                            paragraph_text = "\n".join([p.text for p in p_tags])
                            all_scraper += f"URL: {link_href}\n{paragraph_text}\n"

                            nested_links = page_body.find_elements(By.TAG_NAME, "a")
                            for nested_link in nested_links:
                                nested_href = nested_link.get_attribute("href")

                                if nested_href and nested_href not in visited_urls:
                                    visited_urls.add(nested_href)  
                                    driver.get(nested_href)

                                    nested_page_body = WebDriverWait(driver, 30).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "#pagebody"))
                                    )
                                    nested_p_tags = nested_page_body.find_elements(By.TAG_NAME, "p")[:5]
                                    nested_paragraph_text = "\n".join([p.text for p in nested_p_tags])

                                    all_scraper += f"URL: {nested_href}\n{nested_paragraph_text}\n"

                                    driver.back()

                            driver.back()

                            target_divs = WebDriverWait(driver, 30).until(
                                EC.presence_of_all_elements_located(
                                    (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
                                )
                            )
                            target_div = target_divs[div_index]
                            links = target_div.find_elements(By.TAG_NAME, "a")  

                            link_index += 1 
                        except Exception as e:
                            logger.error(f"Error inesperado procesando el enlace {link_index + 1}: {str(e)}")
                            driver.back()
                            continue

                    break  
                except StaleElementReferenceException:
                    logger.warning(f"Se encontró un 'stale element'. Reintentando ({retry + 1}/3)...")
                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Error inesperado durante el scraping: {str(e)}")
                    raise e

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
        logger.info("Navegador cerrado")

