from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    get_random_user_agent
)

def scraper_ala_org(url, sobrenombre):
    logger = get_logger("ALA_ORG")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    all_hrefs = []  # Lista para almacenar los enlaces
    try:
        driver.get(url)
        
        # Hacer clic en el botón de búsqueda
        btn = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']"))
        )
        btn.click()
        time.sleep(2)

        # Extraer todos los enlaces paginando hasta la última página
        while True:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ol"))
            )

            lis = driver.find_elements(By.CSS_SELECTOR, "ol li.search-result")
            
            for li in lis:
                try:
                    a_tag = li.find_element(By.CSS_SELECTOR, "a")
                    href = a_tag.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            href = url + href[1:]  # Convertir enlaces relativos a absolutos
                        all_hrefs.append(href)  # Guardar en la lista
                except Exception as e:
                    logger.warning(f"Error obteniendo href: {e}")

            # Intentar encontrar el botón de siguiente página
            try:
                next_page_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")
                next_page_url = next_page_btn.get_attribute("href")
                if next_page_url:
                    driver.get(next_page_url)
                    time.sleep(3)
                else:
                    break
            except Exception:
                break  # Si no hay botón de siguiente, terminamos el bucle

    finally:
        driver.quit()  # Cerrar el navegador

    # Ahora procesamos todos los enlaces con requests
    all_scraper = ""
    headers = {"User-Agent": get_random_user_agent()}

    for href in all_hrefs:
        try:
            response = requests.get(href, headers=headers, timeout=10)  # Hacer la petición HTTP
            if response.status_code == 200:
                all_scraper += response.text  # Guardar el contenido
            else:
                logger.warning(f"No se pudo obtener {href}, código {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Error en la solicitud a {href}: {e}")

    # Procesar los datos extraídos y guardarlos
    return process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
