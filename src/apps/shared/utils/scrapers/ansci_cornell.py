import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from rest_framework.response import Response
from rest_framework import status

from ..functions import (
    initialize_driver,
    connect_to_mongo,
    get_logger,
    process_scraper_data,
    save_to_mongo,  
)

def scraper_ansci_cornell(url, sobrenombre):
    logger = get_logger("ANSCI_CORNELL")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    db, fs = connect_to_mongo()  
    
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    
    all_scraper = "URLs encontradas:\n"
    failed_urls = []
    
    try:
        driver.get(url)

        try:
            search_button = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
                )
            ).find_elements(By.TAG_NAME, "a")[1]
            driver.execute_script("arguments[0].click();", search_button)
        except Exception as e:
            logger.error(f"No se encontró el botón de búsqueda: {str(e)}")
            return Response({"message": "No se encontró el botón de búsqueda."}, status=status.HTTP_400_BAD_REQUEST)

        target_divs = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
            )
        )

        if not target_divs:
            logger.warning("No se encontraron secciones de enlaces.")
            return Response({"message": "No se encontraron secciones de enlaces en la página."}, status=status.HTTP_204_NO_CONTENT)

        for target_div in target_divs:
            links = target_div.find_elements(By.TAG_NAME, "a")
            total_links_found += len(links)

            for index, link in enumerate(links):
                retry = 3 
                while retry > 0:
                    try:
                        links = target_div.find_elements(By.TAG_NAME, "a")
                        link = links[index]
                        link_href = link.get_attribute("href")

                        if not link_href:
                            break  

                        driver.get(link_href)
                        content_text = extract_content(driver, link_href, logger)

                        if content_text and content_text.strip():
                            object_id = save_to_mongo("urls_scraper", content_text, link_href, url)
                            total_scraped_successfully += 1

                            logger.info(f"📂 Noticia guardada en `urls_scraper` con object_id: {object_id}")

                        else:
                            failed_urls.append(link_href)
                            total_failed_scrapes += 1
                        
                        driver.back()
                        break 

                    except StaleElementReferenceException:
                        logger.warning(f"Elemento obsoleto en intento {4 - retry}, reintentando...")
                        retry -= 1
                        time.sleep(1)  

        all_scraper += f"\nTotal enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "\nURLs fallidas:\n" + "\n".join(failed_urls)

        response = process_scraper_data(all_scraper, url, sobrenombre,)        
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"message": f"Error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        driver.quit()

def extract_content(driver, link_href, logger):
    content = ""
    try:
        page_body = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#mainContent #pagebody #main"))
        )
        p_tags = page_body.find_elements(By.TAG_NAME, "p")[:5]
        for p in p_tags:
            content += f"{p.text}\n"
    except Exception as e:
        logger.warning(f"No se encontró contenido en {link_href}: {str(e)}")
    return content
