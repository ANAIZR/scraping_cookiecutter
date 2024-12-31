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


def scraper_bugwood(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    base_url = "https://wiki.bugwood.org"
    all_scraper = ""

    try:
        driver.get(url)

        # Espera a que el contenedor del menú esté presente
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#mw-navigation-collapse"))
        )
        container = driver.find_element(By.CSS_SELECTOR, "#mw-navigation-collapse")
        ul_element = container.find_element(By.CSS_SELECTOR, "ul")

        # Procesar todos los <li> en el menú inicial
        list_items = ul_element.find_elements(By.CSS_SELECTOR, "> li")

        for index, li in enumerate(list_items):
            try:
                li_text = li.text.strip()
                if not li_text:
                    logger.info(f"Elemento {index + 1}: (Sin texto visible)")
                    continue

                # Intentar expandir si es un dropdown
                logger.info(f"Procesando menú: {li_text}")
                li.click()  # Clic para expandir

                # Esperar a que el submenú se cargue, si existe
                WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "ul"))
                )
                sub_ul_elements = li.find_elements(By.CSS_SELECTOR, "ul")

                for sub_ul in sub_ul_elements:
                    sub_list_items = sub_ul.find_elements(By.CSS_SELECTOR, "li")
                    for sub_li in sub_list_items:
                        try:
                            # Verificar si el sub-li tiene un enlace
                            link_element = sub_li.find_element(By.CSS_SELECTOR, "a")
                            href = link_element.get_attribute("href")
                            if href and href.startswith(base_url):
                                logger.info(f"Encontrado enlace: {href}")
                                all_scraper+= f"{href}\n"
                        except Exception as e:
                            logger.error(f"Error procesando sub-li: {str(e)}")
                            continue
            except TimeoutException:
                logger.warning(f"Timeout al cargar elementos del menú: {li_text}")
            except Exception as e:
                logger.error(f"Error procesando <li>: {li_text} - {str(e)}")
                continue

        

        # Procesar los datos extraídos
        response = process_scraper_data(
            all_scraper, url, sobrenombre, collection, fs
        )
        return response

    except Exception as e:
        logger.error(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        try:
            driver.quit()
        except Exception as e:
            logger.error(f"Error al cerrar el navegador: {e}")
