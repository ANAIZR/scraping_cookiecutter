from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status

from bs4 import BeautifulSoup
import time 

def scraper_iucngisd(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()

    try:
        driver.get(url)
        print(f"Abriendo URL: {url}")
        search_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#go"))
        )
        print("Botón de búsqueda encontrado.")
        driver.execute_script("arguments[0].click();", search_button)
        print("Haciendo clic en el botón de búsqueda con JavaScript.")
        time.sleep(5)
        print("Esperando 5 segundos para cargar la página.")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.content.spec"))
        )
        print("Esperando a que aparezca el elemento ul.")        
        ul_tag = driver.find_element(By.CSS_SELECTOR, "ul.content.spec")
        if ul_tag:
            print("Elemento ul encontrado.")
        li_tags = ul_tag.find_elements(By.TAG_NAME, "li")
        if li_tags:
            print(f"Elementos li encontrados: {len(li_tags)}")

            for li_tag in li_tags:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "li"))
                )
                href = li_tag.find_element(By.TAG_NAME, "a").get_attribute("href")
                print(f"Enlace encontrado: {href}")
                if href:
                    driver.get(href)
                    print(f"Procesando enlace: {href}")
                    try:
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.ID, "inner-content"))
                        )
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        inner_content = soup.find(id="inner-content").get_text(strip=True)
                        all_scraper += inner_content + "\n\n"
                    except Exception as e:
                        logger.error(f"Error al obtener el contenido interno: {str(e)}")



                    
                else:
                    logger.error("No se encontró un enlace en el tag <a>.")
                    continue

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
