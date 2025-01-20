from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

import time

def scraper_nemaplex(
    url,
    sobrenombre,
):
    logger = get_logger("scraper", sobrenombre)

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#form1"))
        )
        button = driver.find_element(By.CSS_SELECTOR, "#Button1")
        if button.is_enabled():
            button.click()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#GridView1")
                )
            )
            time.sleep(5)

        # Localizar la tabla por el id GridView1
        table = driver.find_element(By.ID, "GridView1")

        # Iterar sobre las filas (tr) de la tabla
        rows = table.find_elements(By.TAG_NAME, "tr")
        data = []  # Lista para almacenar los datos extraídos
        for index, row in enumerate(rows):
            # Extraer columnas dentro de la fila
            columns = row.find_elements(By.TAG_NAME, "td")
            row_data = [col.text for col in columns]  # Obtener texto de cada columna
            logger.info(f"Fila {index}: {row_data}")
            data.append(row_data)

        # Procesar los datos extraídos
        response = process_scraper_data(data, url, sobrenombre, collection, fs)
        return response
    finally:
        driver.quit()
