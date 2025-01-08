from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import json
import time
from bs4 import BeautifulSoup
import traceback

logger = get_logger("scraper")

def load_keywords(file_path="../txt/plants.txt"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(base_path, file_path)
        with open(absolute_path, "r", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if isinstance(line, str) and line.strip()]
        logger.info(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        logger.error(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise


# Espera aleatoria
def random_wait(min_wait=2, max_wait=6):
    wait_time = random.uniform(min_wait, max_wait)
    logger.info(f"Esperando {wait_time:.2f} segundos...")
    time.sleep(wait_time)
    
def scrape_links(driver, url, keyword):
    if not isinstance(keyword, str):
        logger.error(f"La palabra clave no es una cadena válida: {keyword}")
        return []

    logger.info(f"Procesando palabra clave: {keyword}")
    driver.get(url)

    search_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#gs_hdr_tsi"))
    )
    search_box.clear()
    search_box.send_keys(keyword)

    search_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#gs_hdr_tsb"))
    )
    search_button.click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#gs_res_ccl_mid"))
    )
    logger.info(f"Resultados cargados para: {keyword}")

    output_dir = "c:/web_scraper_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_folder_path = generate_directory(output_dir, url)

    sanitized_keyword = keyword.lower().replace(' ', '_').replace('.', '').replace(',', '')
    keyword_folder = generate_directory(base_folder_path, sanitized_keyword)
    
    existing_files = os.listdir(keyword_folder)
    max_index = -1
    for file in existing_files:
        if file.startswith("link_v") and file.endswith(".txt"):
            try:
                file_index = int(file[6:-4])
                max_index = max(max_index, file_index)
            except ValueError:
                continue
    index = max_index + 1

    all_links = []
    visited_urls = set()

    while True:
        current_page_url = driver.current_url
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        links = soup.select("div.gs_ri h3 a")
        print(f"Se encontraron {len(links)} links")
        
        for index, link in enumerate(links):
            result = link.get("href")
            print(f"Enlace encontrado: {result}")

            if result not in visited_urls:
                try:
                    if "download" in result.lower():
                        print(f"El enlace {result} contiene 'download'. No se hará back.")
                        continue
                    
                    driver.get(result)
                    time.sleep(2)

                    body_content = driver.find_element(By.TAG_NAME, "body").text.strip()
                    if body_content:
                        try:
                            error_element = driver.find_element_by_class_name("error-code")
                            if error_element:
                                print(f"Se encontró 'div.error-code' en la página {result}. Volviendo atrás.")
                                print(f"{current_page_url} url")
                                driver.get(current_page_url)
                                time.sleep(3)
                                
                        except Exception:
                            driver.back()
                            time.sleep(3)
                            pass

                        logger.info(f"Contenido extraído del enlace: {result}")
                        
                        file_path = os.path.join(keyword_folder, f"link_v{index}.txt")
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(f"URL: {result}\n{body_content}\n")
                        
                        all_links.append({"url": result, "content": body_content})
                        visited_urls.add(result)
                        index += 1
                        driver.get(current_page_url)
                        time.sleep(3)
                    else:
                        print(f"No se encontró contenido en el body")
                        driver.get(current_page_url) 
                        time.sleep(3)
                        pass
                        
                except Exception as e:
                    print(f"No se pudo acceder al link {result}: {e}")
                    driver.get(current_page_url) 
                    time.sleep(3)
        
        if "start=20" in current_page_url:
            print(f"Se alcanzó la página 10 para '{keyword}'. Fin del scraping para esta palabra.")
            break

        next_button_clicked = False
        try:
            next_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div#gs_n td:nth-child(12) b"))
            )
            print("Next button encontrado")
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(2)
            next_button_clicked = True
        except Exception as e:
            print("Error con el botón principal:")
            traceback.print_exc()

        if not next_button_clicked:
            try:
                button_contigencia = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div#gs_nm .gs_btnPR"))
                )
                print("Next button encontrado Contingencia")
                driver.execute_script("arguments[0].click();", button_contigencia)
                time.sleep(2)
                next_button_clicked = True
            except Exception as e:
                print("Error con el botón contingencia:")
                traceback.print_exc()

        if not next_button_clicked:
            print(f"No se pudo hacer clic en ningún botón 'Siguiente' para '{keyword}'. Fin del scraping para esta palabra.")
            break

    return all_links

def scraper_google_academic(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    keywords = load_keywords()
    results = {}

    try:
        for keyword in keywords:
            random_wait()

            logger.info(f"Iniciando scraping para la palabra clave: {keyword}")
            links = scrape_links(driver, url, keyword)

            if not isinstance(keyword, str):
                logger.error(f"Palabra clave no válida: {keyword}")
                continue

            results[keyword] = links

        if not isinstance(results, dict):
            raise ValueError("Los resultados no son un diccionario válido.")

        results_json = json.dumps(results, ensure_ascii=False)

        response = process_scraper_data(results_json, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
