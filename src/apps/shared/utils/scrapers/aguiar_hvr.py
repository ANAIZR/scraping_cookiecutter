from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = get_logger("INICIANDO EL SCRAPER")

class ScraperState:
    def __init__(self):
        self.all_scraper = ""
        self.processed_links = set()
        self.extracted_hrefs = []  
        self.skipped_count = 0
        self.extracted_count = 0

def wait_for_element(driver, wait_time, locator):
    try:
        return WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(locator)
        )
    except TimeoutException as e:
        logger.error(f"Elemento no encontrado: {locator} - {str(e)}")
        raise

def extract_internal_hrefs(driver, state):
    try:
        divs = driver.find_elements(By.CSS_SELECTOR, "div.col-md-2.col-sm-4.col-xs-6")
        logger.info(f"{len(divs)} divs encontrados con enlaces internos.")
        for div in divs:
            try:
                href = div.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                state.extracted_hrefs.append(href)
                logger.info(f"Href extraído: {href}")
            except Exception as e:
                logger.warning(f"No se pudo extraer el href del div: {str(e)}")
    except Exception as e:
        logger.error(f"Error al extraer los hrefs internos: {str(e)}")

def process_table_rows(driver, state):
    rows = driver.find_elements(By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody tr")
    logger.info(f"{len(rows)} filas encontradas en la tabla.")
    for row in rows:
        try:
            link = row.find_element(By.CSS_SELECTOR, "td a").get_attribute("href")
            if link not in state.processed_links:
                state.processed_links.add(link)
                logger.info(f"Ingresando al href de la tabla: {link}")
                driver.get(link)  
                extract_internal_hrefs(driver, state)  
                driver.back()  
                wait_for_element(driver, 10, (By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody"))
        except Exception as e:
            logger.error(f"Error procesando fila de la tabla: {str(e)}")
def get_current_page_number(driver):
    try:
        page_number_element = driver.find_element(By.CSS_SELECTOR, ".pagination .active a")
        page_number = int(page_number_element.text)
        logger.info(f"Página actual: {page_number}")
        return page_number
    except Exception as e:
        logger.error(f"No se pudo obtener el número de página actual: {str(e)}")
        return None

def click_next_page(driver, wait_time):
    try:
        next_button = wait_for_element(
            driver, wait_time, (By.CSS_SELECTOR, "#DataTables_Table_0_next a")
        )
        logger.info(f"Estado del botón 'Siguiente': {next_button.get_attribute('class')}")

        if "disabled" in next_button.get_attribute("class") or not next_button.is_enabled():
            logger.info("Botón de siguiente página deshabilitado. Fin de la paginación.")
            return False

        current_page = get_current_page_number(driver)
        next_button.click()
        logger.info(f"Haciendo clic en la página siguiente desde la página {current_page}.")

        WebDriverWait(driver, wait_time).until(
            lambda d: get_current_page_number(d) != current_page
        )
        return True
    except TimeoutException:
        logger.error("Tiempo de espera agotado al intentar cambiar de página.")
        return False
    except Exception as e:
        logger.error(f"Error al intentar ir a la siguiente página: {str(e)}")
        return False

def scrape_content_from_links(state):
    def process_link(link):
        try:
            response = requests.get(link, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                content = soup.find("div", class_="parteesq")
                if content:
                    text = content.get_text(strip=True)
                    logger.info(f"Contenido extraído de: {link}")
                    return link, text, None  # Devuelve el enlace y el contenido
                else:
                    logger.warning(f"No se encontró contenido en: {link}")
                    return link, None, "No se encontró contenido"
            else:
                logger.warning(f"Error al solicitar {link}: Status {response.status_code}")
                return link, None, f"Status {response.status_code}"
        except Exception as e:
            logger.error(f"Error al procesar {link}: {str(e)}")
            return link, None, str(e)

    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_link = {executor.submit(process_link, link): link for link in state.extracted_hrefs}

        for future in as_completed(future_to_link):
            link = future_to_link[future]
            try:
                link, text, error = future.result()
                if text:
                    state.all_scraper += f"URL: {link}\nContenido: {text}\n\n"
                    state.extracted_count += 1
                elif error:
                    logger.warning(f"Error procesando {link}: {error}")
                    state.skipped_count += 1
            except Exception as e:
                logger.error(f"Error desconocido al procesar {link}: {str(e)}")
                state.skipped_count += 1

def scraper_aguiar_hvr(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    state = ScraperState()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    try:
        driver.get(url)
        while True:
            wait_for_element(driver, 30, (By.CSS_SELECTOR, "#DataTables_Table_0_wrapper tbody"))
            process_table_rows(driver, state) 
            if not click_next_page(driver, 30): 
                break

        logger.info(f"Se recolectaron {len(state.extracted_hrefs)} enlaces. Procesando contenido...")
        scrape_content_from_links(state) 

        response = process_scraper_data(state.all_scraper, url, sobrenombre, collection, fs)
        return response
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        driver.quit()
