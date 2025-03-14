from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    save_to_mongo
)

def scraper_flmnh_ufl(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()

    try:
        collection, fs = connect_to_mongo()
    except Exception as e:
        logger.error(f"Error al conectar a MongoDB: {str(e)}")
        return Response(
            {"error": f"Error al conectar a MongoDB: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    all_scraper = f"{url}\n\n"
    total_scraped_successfully = 0

    def scrape_page():
        nonlocal all_scraper, total_scraped_successfully
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "table.x-grid-table tbody tr")
                )
            )
            soup = BeautifulSoup(driver.page_source, "html.parser")
            rows = soup.select("table.x-grid-table tbody tr:not(.x-grid-header-row)")

            for row in rows:
                cols = row.find_all("td")
                data = [col.text.strip() for col in cols]
                all_scraper += " | ".join(data) + "\n"

                links = row.find_all("a", href=True)
                for link in links:
                    link_href = link["href"]
                    driver.get(link_href)
                    time.sleep(2)
                    content_soup = BeautifulSoup(driver.page_source, "html.parser")
                    content_text = content_soup.get_text()

                    if content_text and content_text.strip():
                        object_id = save_to_mongo("urls_scraper", content_text, link_href, url)
                        total_scraped_successfully += 1
                        
                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                        
        except Exception as e:
            logger.error(f"Error durante el scraping de la página: {str(e)}")
            raise e
    def go_to_next_page(max_pages=3):
        page_count = 0  

        while page_count < max_pages:
            try:
                WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.ID, "button-1065-btnEl"))
                )
                next_button = driver.find_element(By.ID, "button-1065-btnEl")
                driver.execute_script("arguments[0].click();", next_button)
                logger.info(f"Clic en el botón de siguiente página ({page_count + 1}/{max_pages})")
                
                page_count += 1  
                time.sleep(3) 
            except Exception as e:
                logger.warning(f"No se pudo hacer clic en el botón de siguiente página: {str(e)}")
                break  

        logger.info("Se alcanzó el límite de navegación o no hay más páginas.")

    
    
    
    
    """def go_to_next_page():
        try:
            WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "button-1065-btnEl"))
            )
            next_button = driver.find_element(By.ID, "button-1065-btnEl")
            driver.execute_script("arguments[0].click();", next_button)
            logger.info("Clic en el botón de siguiente página")
            return True
        except Exception as e:
            logger.warning(
                f"No se pudo hacer clic en el botón de siguiente página: {str(e)}"
            )
            return False"""

    try:
        driver.get(url)
        logger.info(f"URL cargada: {url}")

        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl"))
        )
        btn = driver.find_element(By.CSS_SELECTOR, "#adv-srch-btn-btnInnerEl")
        driver.execute_script("arguments[0].click();", btn)

        scrape_page()

        while go_to_next_page():
            time.sleep(2)
            scrape_page()

        response = process_scraper_data(all_scraper, url, sobrenombre,collection)
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado")
