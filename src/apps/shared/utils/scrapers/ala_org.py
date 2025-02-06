from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
import random

def scraper_ala_org(url, sobrenombre):
    logger = get_logger("ALA_ORG")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    all_scraper = ""

    try:
        driver.get(url)

        try:
            button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            driver.execute_script("arguments[0].click();", button)
            time.sleep(random.randint(1, 3))
        except Exception as e:
            logger.error(f"No se pudo hacer clic en el botón de búsqueda: {e}")
            return {"error": "No se encontró el botón de búsqueda"}

        while True:
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ol li.search-result"))
                )

                lis = driver.find_elements(By.CSS_SELECTOR, "ol li.search-result")

                for li in lis:
                    try:
                        a_tag = li.find_element(By.CSS_SELECTOR, "a")
                        href = a_tag.get_attribute("href")
                        if href:
                            if href.startswith("/"):
                                href = url + href[1:]

                            logger.info(f"Accediendo a {href}")

                            ActionChains(driver).move_to_element(a_tag).click().perform()

                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "section.container-fluid"))
                            )

                            content = driver.find_element(By.CSS_SELECTOR, "section.container-fluid")
                            all_scraper += f"URL: {href}\n{content.text}\n\n"

                            try:
                                driver.back()
                                time.sleep(random.randint(2, 4))
                            except Exception as e:
                                logger.warning(f"No se pudo regresar a la página de resultados, recargando URL: {url}")
                                driver.get(url)
                                time.sleep(random.randint(2, 4))

                    except Exception as e:
                        logger.warning(f"No se pudo hacer clic en el enlace o procesar el <li>: {e}")
                        continue

                try:
                    next_page_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")
                    next_page_url = next_page_btn.get_attribute("href")
                    if next_page_url:
                        logger.info(f"Navegando a la siguiente página: {next_page_url}")
                        driver.get(next_page_url)
                        time.sleep(3)
                    else:
                        break
                except Exception as e:
                    logger.warning("No se encontró el botón de siguiente página, terminando el scraping.")
                    break

            except Exception as e:
                logger.error(f"Error al cargar los resultados: {e}")
                break

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("Navegador cerrado")

