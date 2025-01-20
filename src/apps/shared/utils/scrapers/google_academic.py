from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    get_next_versioned_filename,
    process_scraper_data_without_file
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import json
import time
from bs4 import BeautifulSoup
import requests
import re

logger = get_logger("scraper", "google_academic")

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


def random_wait(min_wait=2, max_wait=6):
    wait_time = random.uniform(min_wait, max_wait)
    logger.info(f"Esperando {wait_time:.2f} segundos...")
    time.sleep(wait_time)

def download_pdf(url, save_path):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' in content_disposition:
                filename = re.findall('filename="(.+)"', content_disposition)
                if filename:
                    save_path = os.path.join(os.path.dirname(save_path), filename[0])

            base_name, ext = os.path.splitext(save_path)
            counter = 0
            save_path = f"{base_name}_v{counter}{ext}"  
            while os.path.exists(save_path):
                counter += 1
                save_path = f"{base_name}_v{counter}{ext}"

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Archivo descargado en: {save_path}")
        else:
            print(f"Error al descargar el archivo. Código de estado: {response.status_code}")
    except Exception as e:
        print(f"Error durante la descarga del PDF: {e}")

        
def is_pdf(url):
    try:
        response = requests.head(url, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '')
        return "application/pdf" in content_type
    except Exception as e:
        print(f"Error al verificar el tipo de contenido: {e}")
        return False

def is_valid_href(url):
    """
    Verifica si el URL es válido y accesible.
    """
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        if response.status_code != 420:
            return True
        else:
            print(f"El enlace {url} devolvió un código HTTP {response.status_code}. Ignorando.")
            return False
    except Exception as e:
        print(f"Error al verificar el enlace {url}: {e}")
        return False

def scraper_google_academic(url, sobrenombre):
    print(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    keywords = load_keywords()
    

    base_folder_path = generate_directory(url)
    results = {}

    try:
        for keyword in keywords:
            if not isinstance(keyword, str):
                print(f"La palabra clave no es una cadena válida: {keyword}")
                continue

            driver.get(url)
            print(f"Procesando palabra clave: {keyword}")

            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#gs_hdr_tsi"))
            )
            search_box.clear()
            search_box.send_keys(keyword)
            time.sleep(random.uniform(2, 5))
            search_box.submit()
            time.sleep(random.uniform(2, 5))

            """ search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#gs_hdr_tsb"))
            )
            search_button.click() """

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#gs_res_ccl_mid"))
            )

            sanitized_keyword = re.sub(r'[^\w\-_]', '_', keyword.lower().replace(' ', '_'))[:50]
            keyword_folder = generate_directory(sanitized_keyword, base_folder_path)

            all_links = []
            visited_urls = set()

            while True:
                current_page_url = driver.current_url
                soup = BeautifulSoup(driver.page_source, "html.parser")
                links = soup.select("div.gs_ri h3 a")

                for link in links:
                    result = link.get("href")

                    if result not in visited_urls:
                        try:
                            response = requests.head(result, allow_redirects=True, timeout=10)
                            if response.status_code == 420:
                                print(f"El enlace {result} devolvió un código HTTP 420. Ignorando.")
                                continue

                            href_name = re.sub(r'[^\w\-_]', '_', result.split("/")[-1])[:50]

                            link_folder = generate_directory(href_name, keyword_folder)

                            file_base_name = href_name

                            if "download" in result.lower() or is_pdf(result):
                                try:
                                    save_path = get_next_versioned_filename(link_folder, sobrenombre)
                                    if not save_path.lower().endswith(".pdf"):
                                        save_path += ".pdf"

                                    if not os.path.exists(save_path):
                                        download_pdf(result, save_path)
                                        visited_urls.add(result)
                                    continue
                                except Exception as e:
                                    print(f"Error al descargar el PDF: {e}")

                            if "books.google" in result:
                                print("**********************Es un ebook. Extrayendo contenido de div#menu_scroll_wrapper.")
                                driver.get(result)
                                time.sleep(3)
                                try:
                                    menu_wrapper = WebDriverWait(driver, 60).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "div#menu_scroll_wrapper"))
                                    )
                                    menu_content = menu_wrapper.text.strip() if menu_wrapper else ""
                                    if menu_content:                                       
                                        file_path = get_next_versioned_filename(link_folder, sobrenombre)
                                        with open(file_path, "w", encoding="utf-8") as f:
                                            f.write(f"URL: {result}\n{menu_content}\n")
                                        print(f"Archivo guardado en: {file_path}")
                                    else:
                                        print(f"No se pudo capturar el contenido del div#menu_scroll_wrapper para el link: {result}")
                                except Exception as e:
                                    print(f"Error al capturar el contenido del div#menu_scroll_wrapper: {e}")
                                visited_urls.add(result)
                                driver.back()
                                continue

                            driver.get(result)
                            time.sleep(2)
                            

                            body_element = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                            body_content = body_element.text.strip() if body_element else ""

                            if body_content:
                                cleaned_body_content = ' '.join(body_content.split())
                                print(f"Contenido capturado:\n{cleaned_body_content[:500]}")

                                file_path = get_next_versioned_filename(link_folder, sobrenombre)
                                if not os.path.exists(file_path):
                                    with open(file_path, "w", encoding="utf-8") as f:
                                        f.write(f"URL: {result}\n{cleaned_body_content}\n")
                                    print(f"Archivo guardado en: {file_path}")

                                all_links.append({"url": result, "content": cleaned_body_content})
                                visited_urls.add(result)
                                driver.get(current_page_url)
                                time.sleep(3)
                            else:
                                print(f"No se pudo capturar el contenido del body para el link: {result}")

                        except Exception as e:
                            print(f"No se pudo acceder al link {result}: {e}")
                            driver.get(current_page_url)
                            time.sleep(3)

                if "start=20" in current_page_url:
                    print(f"Se alcanzó la página 10 para '{keyword}'. Fin del scraping para esta palabra.")
                    break

                try:
                    next_button = WebDriverWait(driver, 30).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div#gs_n td:nth-child(12) b"))
                    )
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(2)
                except Exception:
                    break

            results[keyword] = all_links

        results_json = json.dumps(results, ensure_ascii=False)
        response = process_scraper_data_without_file(results_json, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        print(f"Error durante el scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
