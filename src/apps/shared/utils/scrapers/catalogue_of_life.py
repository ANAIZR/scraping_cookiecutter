from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import time

logger = get_logger("scraper")


# Cargar palabras clave desde utils/txt/all.txt
def load_keywords(file_path="../txt/all.txt"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(base_path, file_path)
        with open(absolute_path, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]
        #logger.info(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        logger.error(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise


def scraper_catalogue_of_life(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    keywords = load_keywords()  
    results = {}

    try:
        driver.get(url)
        logger.info("Página cargada exitosamente.")

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "search_string"))
        )
        logger.info("Barra de búsqueda localizada.")

        # Iterar por cada fila
        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")
            # Introducir un tiempo de espera aleatorio antes de interactuar con el buscador
            random_wait()

            # Ingresar la palabra clave y presionar Enter
            search_box.clear()
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )
            logger.info(f"Resultados cargados para: {keyword}")

            # Obtener todas las filas de la tabla de resultados
            rows = driver.find_elements(By.XPATH, "//tr[starts-with(@id, 'record_')]")
            print(f"Rows encontrados {len(rows)}")
            
            # Iterar sobre las filas de resultados
            for index, row in enumerate(rows):
                record_id = row.get_attribute("id")
                print(f"Procesando fila con id: {record_id}")

                try:
                    # Obtener el siguiente tr hermano del tr con id="record_..."
                    next_row = row.find_element(By.XPATH, "following-sibling::tr")

                    first_td = next_row.find_element(By.TAG_NAME, "td")
                    # Verificar si el td tiene un enlace (href)
                    link = first_td.find_element(By.TAG_NAME, "a")
                    if link and link.get_attribute("href"):
                        href = link.get_attribute("href")
                        print(f"Accediendo al enlace: {href}")
                        
                        # Hacer clic en el enlace para ir a la página de detalles
                        driver.get(href)

                        # Esperar a que se cargue el contenido de la página de detalles
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                        )

                        # Realizar el scraping del contenido de la página
                        page_content = driver.page_source
                        print("Despues de page_content")

                        # Guardar los resultados del enlace
                        results[href] = page_content

                        # Regresar a la página de resultados
                        driver.back()

                        # Esperar un poco antes de continuar con el siguiente enlace
                        random_wait()
                    
                except Exception as e:
                    logger.error(f"Error procesando el enlace en la fila con id {record_id}: {str(e)}")

                # Re-actualizar la lista de filas para el siguiente ciclo después de regresar
                if index < len(rows) - 1:
                    rows = driver.find_elements(By.XPATH, "//tr[starts-with(@id, 'record_')]")

        # Limpiar los resultados después de procesar la palabra clave
            logger.info(f"Palabra clave {keyword} procesada. Acumulando resultados.")


        # Una vez que se han procesado todas las palabras clave, procesar los datos
        response = process_scraper_data(results, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()


# Función auxiliar para introducir un tiempo de espera aleatorio
def random_wait(min_wait=2, max_wait=6):
    wait_time = random.uniform(min_wait, max_wait)
    logger.info(f"Esperando {wait_time:.2f} segundos...")
    time.sleep(wait_time)
