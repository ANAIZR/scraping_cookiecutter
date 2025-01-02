from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status
import time


def scraper_bugwood(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    base_url = "https://wiki.bugwood.org"
    all_scraper = ""

    try:
        driver.get(url)
        print("Pagina cargada")
        # Espera a que el contenedor del menú esté presente
        container = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#mw-navigation-collapse"))
        )
        if container:
            print("Contenedor encontrado")
            ul_element = container.find_element(By.CSS_SELECTOR, "ul")
            list_items = ul_element.find_elements(By.CSS_SELECTOR, "li.dropdown")
            print(f"Elementos encontrados: {len(list_items)}")
            for item in list_items:
                li_text = item.text.strip()
                if not li_text:
                    continue
                all_scraper += f"Elemento {li_text} \n\n"
                item.click()
                container_ul = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul[id^='p-']"))
                )
                if container_ul:
                    print("Contenedor de subelementos encontrado")
                    subitems = WebDriverWait(driver, 30).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "ul[id^='p-'] li[id^='n-']")
                        )
                    )
                    if subitems:
                        print(f"ITEMS ENCONTRADOS {li_text}: {len(subitems)}")
                        print(f"Subelementos encontrados: {len(subitems)}")

                        for subitem in subitems:
                            subitem_text = subitem.text.strip()

                            all_scraper += f"Subelemento {subitem_text} \n\n"

                else:
                    print("No se encontró el contenedor de subelementos")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        try:
            driver.quit()
        except Exception as e:
            logger.error(f"Error al cerrar el navegador: {e}")
