import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
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

        # Intentar hacer clic en el botón de navegación con reintentos
        try:
            search_button = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#section-navigation li:nth-of-type(3)")
                )
            ).find_elements(By.TAG_NAME, "a")[1]
            search_button.click()
        except Exception as e:
            logger.error(f"No se encontró el botón de búsqueda: {str(e)}")
            return Response({"message": "No se encontró el botón de búsqueda."}, status=status.HTTP_400_BAD_REQUEST)

        # Esperar y encontrar los divs
        target_divs = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#pagebody div[style*='float: left; width:32%;']")
            )
        )

        if not target_divs:
            logger.warning("No se encontraron secciones de enlaces.")
            return Response({"message": "No se encontraron secciones de enlaces en la página."}, status=status.HTTP_204_NO_CONTENT)

        # Iterar sobre los divs y extraer los enlaces
        for target_div in target_divs:
            links = target_div.find_elements(By.TAG_NAME, "a")

            for index, link in enumerate(links):
                retry = 3  # Intentos en caso de StaleElementReferenceException
                while retry > 0:
                    try:
                        # Volver a encontrar el enlace antes de usarlo
                        links = target_div.find_elements(By.TAG_NAME, "a")
                        link = links[index]
                        link_href = link.get_attribute("href")

                        if not link_href:
                            break  # Si no hay href, pasar al siguiente

                        driver.get(link_href)
                        all_scraper += extract_content(driver, link_href, logger)
                        driver.back()

                        break  # Si el proceso se completa sin errores, salir del bucle de reintentos

                    except StaleElementReferenceException:
                        logger.warning(f"Elemento obsoleto en intento {4 - retry}, reintentando...")
                        retry -= 1
                        time.sleep(1)  # Pequeño retraso antes de reintentar

        # Procesar los datos extraídos
        response_data = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)

        if isinstance(response_data, dict):
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return response_data

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"message": f"Error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        driver.quit()


def extract_content(driver, link_href, logger):
    """
    Extrae el contenido de la página actual y accede a los enlaces dentro de ella.
    """
    content = f"URL: {link_href}\n"

    try:
        # Esperar a que se cargue el contenido del ID "main"
        page_body = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#mainContent #pagebody #main"))
        )

        # Extraer el texto de los primeros 5 párrafos
        p_tags = page_body.find_elements(By.TAG_NAME, "p")[:5]
        for p in p_tags:
            content += f"{p.text}\n"

        # Extraer enlaces dentro de esta página
        nested_links = page_body.find_elements(By.TAG_NAME, "a")
        for nested_link in nested_links:
            nested_href = nested_link.get_attribute("href")
            if nested_href:
                driver.get(nested_href)
                time.sleep(2)  # Esperar para evitar bloqueos por carga rápida
                content += extract_content(driver, nested_href, logger)  # Llamada recursiva
                driver.back()  # Volver a la página original

    except Exception as e:
        logger.warning(f"No se encontró contenido en {link_href}: {str(e)}")

    content += "**********\n"
    return content
