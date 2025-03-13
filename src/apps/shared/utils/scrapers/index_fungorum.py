from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
import os
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework.response import Response
from rest_framework import status
import time
import random
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    get_random_user_agent
)
urls_to_scrape = []  
non_scraped_urls = []  
scraped_urls = []

url_padre=""
fs = None
headers = None
logger = get_logger("scraper")

def load_search_terms(file_path):
    try:
        with open(file_path, "r") as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except Exception as e:
        print(f"Error al cargar términos: {e}")
        return []


def extract_text(current_url):
    global scraped_urls
    try:
        response = requests.get(current_url, headers=headers)
        response.raise_for_status()
        print(f"Procesando URL by quma: {current_url}")

        soup = BeautifulSoup(response.content, "html.parser")

        table_element = soup.find("table", class_="mainbody")
        # print("Table:", table_element)
        if table_element:

            body_text = table_element.get_text(separator=" ", strip=True)
            print("texto by qumadev: ",body_text)
            if body_text:
                object_id = fs.put(
                    body_text.encode("utf-8"),
                    source_url=current_url,
                    scraping_date=datetime.now(),
                    Etiquetas=["planta", "plaga"],
                    contenido=body_text,
                    url=url_padre
                )
                scraped_urls += 1
                scraped_urls.append(current_url)
                print(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                existing_versions = list(fs.find({"source_url": current_url}).sort("scraping_date", -1))
                if len(existing_versions) > 1:
                    oldest_version = existing_versions[-1]
                    file_id = oldest_version._id  # Esto obtiene el ID correcto
                    fs.delete(file_id)  # Eliminar la versión más antigua
                    logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
            else:
                non_scraped_urls.append(current_url)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error al procesar la URL {current_url}: {e}")


def scrape_pages_in_parallel(url_list):
    print("Scraping pages in parallel")
    global non_scraped_urls
    new_links = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_url = {
            executor.submit(extract_text, url): (url)
            for url in url_list
        }
        for future in as_completed(future_to_url):
            try:
                result_links = future.result()
                new_links.extend(result_links)
            except Exception as e:
                logger.error(f"Error en tarea de scraping: {str(e)}")
                non_scraped_urls += 1
    return new_links

def scraper_index_fungorum(url, sobrenombre):
    global url_padre,headers,fs,scraped_urls,non_scraped_urls

    url_padre = url

    search_terms = load_search_terms(
        os.path.join(os.path.dirname(__file__), "../txt/plants.txt")
    )

    if not search_terms:
        return Response(
            {"error": "No se encontraron términos para buscar."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    headers = {"User-Agent": get_random_user_agent()}
    all_scraper = ""
    try:
        driver.get(url)

        for term in search_terms:
            try:

                input_field = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "SearchTerm"))
                )
                input_field.clear()
                input_field.send_keys(term)

                btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                btn.click()

                time.sleep(random.uniform(3, 6))
                logger.info(f"Realizando búsqueda con la palabra clave: {term}")

                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.mainbody"))
                )
                time.sleep(random.uniform(3, 6))
                logger.info("Búsqueda realizada con éxito")

                number_page = 1
                while True:
                    links = driver.find_elements(By.CSS_SELECTOR, "a.LinkColour1")
                    if not links:
                        continue

                    for link in links:
                        href = link.get_attribute("href")
                        if "NamesRecord" in href:
                            urls_to_scrape.append(href)
                            print("href by qumadev", href)

                    try:
                        print("inicio de capturar el boton de next")
                        next_link = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'[Next >>]')]"))
                        )
                        next_page_link = next_link.get_attribute("href")

                        if next_page_link:
                            next_link.click()
                            time.sleep(random.uniform(3,6))
                            number_page += 1
                            print(f"=========================== Siguiente página: {number_page} ===========================")
                            driver.get(next_page_link)
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "table.mainbody"))
                            )
                        else:
                            print("No more pages.")
                            break
                    except (TimeoutException, NoSuchElementException):
                        break
                    except Exception as e:
                        print(f"Error during pagination: {e}")
                        break

                    input_field = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.NAME, "SearchTerm"))
                    )
                    input_field.clear()  

                urls_scrappeds = scrape_pages_in_parallel(urls_to_scrape)

                driver.get(url)

                input_field = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "SearchTerm"))
                )

            except Exception as e:
                pass


        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response


    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
