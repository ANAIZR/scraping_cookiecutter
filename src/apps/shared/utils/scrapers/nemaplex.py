from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from datetime import datetime
from bson import ObjectId
import time

def scraper_nemaplex(
    url,
    sobrenombre,
):
    non_scraped_urls = []  
    scraped_urls = []
    total_scraped_links = 0
    logger = get_logger("scraper")

    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
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
            # logger.info(f"Fila {index}: {row_data}")
            data.append(row_data)

            href = url + f"-{index}" 
            print("href by quma: ", href)

            if row_data:
                object_id = fs.put(
                    row_data.encode("utf-8"),
                    source_url=href,
                    scraping_date=datetime.now(),
                    Etiquetas=["planta", "plaga"],
                    contenido=row_data,
                    url=url
                )
                total_scraped_links += 1
                scraped_urls.append(href)
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                if len(existing_versions) > 1:
                    oldest_version = existing_versions[-1]
                    file_id = oldest_version._id  # Esto obtiene el ID correcto
                    fs.delete(file_id)  # Eliminar la versión más antigua
                    logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
            else:
                non_scraped_urls.append(href)

        # Procesar los datos extraídos
        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
    finally:
        driver.quit()
