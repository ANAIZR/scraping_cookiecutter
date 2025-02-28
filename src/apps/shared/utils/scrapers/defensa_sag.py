from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    load_keywords,
    extract_text_from_pdf,
)
import time
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from bs4 import BeautifulSoup

def scraper_defensa_sag(url, sobrenombre):
    logger = get_logger("DEFENSA SAG")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    all_scraper = ""
    scraped_urls = set()
    failed_urls = set()
    visited_urls = set()
    object_ids = []

    try:
        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)

        print(f"✅ Página cargada correctamente.")

        try:
            table_element = driver.find_element(By.CSS_SELECTOR, "table tbody tr td table:nth-child(2) tr td table")
            print("✅ Se encontró las opciones del table")
            logger.info("✅ Se encontró las opciones del table")

            index = 2

            while True:
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, f"tr.sttr:nth-child({index})")

                    if not rows:
                        print("✅ No hay más filas pares para procesar.")
                        break

                    row = rows[0]
                    span_element = row.find_element(By.CSS_SELECTOR, "span")
                    span_text = span_element.text.strip()

                    row.click()
                    time.sleep(2) 

                    print(f"🟢 El nombre del tr es: {span_text}")
                    logger.info(f"🟢 El nombre del tr es: {span_text}")

                    index += 2

                except NoSuchElementException:
                    print(f"⚠️ No se encontró el span en la fila {index}.")
                    logger.warning(f"⚠️ No se encontró el span en la fila {index}.")
                    index += 2

                except StaleElementReferenceException:
                    print(f"🔄 Elemento obsoleto en la fila {index}, reintentando...")
                    logger.warning(f"🔄 Elemento obsoleto en la fila {index}, reintentando...")
                    time.sleep(1)

        except NoSuchElementException:
            print("❌ No se encontró el table especificado")
            logger.error("❌ No se encontró el table especificado")
            return {"error": "No se encontró el table especificado"}

    except Exception as e:
        print(f"⚠️ Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        print("🚪 Navegador cerrado.")
