import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from rest_framework.response import Response
from rest_framework import status
from ..functions import process_scraper_data, get_logger, connect_to_mongo


def scraper_iucngisd(url, sobrenombre):
    logger = get_logger("scraper")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        logger.info("Inicializando navegador.")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

        try:
            logger.info("Conectando a MongoDB.")
            collection, fs = connect_to_mongo("scrapping-can", "collection")
        except Exception as e:
            logger.error(f"Error al conectar con MongoDB: {str(e)}", exc_info=True)
            return Response(
                {"error": "Error al conectar con la base de datos."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"Accediendo a la URL: {url}")
        driver.get(url)

        wait_time = random.randint(3, 6)
        logger.info(
            f"Esperando {wait_time} segundos para que cargue el botón de búsqueda."
        )
        search_button = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#go"))
        )
        search_button.click()

        wait_time = random.randint(3, 6)
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.content.spec"))
        )

        logger.info("Extrayendo datos de la página.")
        ul_tag = driver.find_element(By.CSS_SELECTOR, "ul.content.spec")
        li_tags = ul_tag.find_elements(By.TAG_NAME, "li")

        total_li = len(li_tags)
        total_scraped = 0
        all_scraper = ""

        for li_tag in li_tags:
            wait_time = random.randint(2, 6)
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "li"))
            )
            soup = BeautifulSoup(li_tag.get_attribute("outerHTML"), "html.parser")
            text_content = soup.get_text(separator="\n", strip=True)
            all_scraper += text_content + "\n\n"
            total_scraped += 1

        all_scraper = (
            f"Total de elementos 'li' encontrados: {total_li}\n"
            f"Total de elementos 'li' scrapados: {total_scraped}\n\n" + all_scraper
        )

        logger.info("Procesando los datos del scraping.")
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response

    except Exception as e:
        logger.error(f"Error en el scraping: {str(e)}", exc_info=True)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("El navegador se ha cerrado correctamente.")
