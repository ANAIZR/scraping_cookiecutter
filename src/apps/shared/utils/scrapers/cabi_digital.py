from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pickle
import random
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    uc_initialize_driver,
    get_logger,
    connect_to_mongo_cabi,
    save_to_mongo,
    load_keywords,
    process_scraper_data_v2
)
from rest_framework.response import Response
from rest_framework import status
from ..credentials import login_cabi_scienceconnect
from bson import ObjectId
from ...models.scraperURL import Species,ScraperURL, NewSpecies
import ollama
import json
from pymongo import MongoClient
import gridfs  
import re
from celery import Celery
import requests
import json
from celery import Celery
logger = get_logger("scraper")




def scraper_cabi_digital(url, sobrenombre):
    driver = uc_initialize_driver()
    total_scraped_links = 0
    scraped_urls = []
    non_scraped_urls = []
    object_ids = []

    try:
        if login_cabi_scienceconnect(driver):
            print("Login completado, continuando con el scraping...")
    except:
        logger.error("No se encontro el login")
    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
        collection, fs = connect_to_mongo_cabi()
        keywords = load_keywords("plants.txt")
        if not keywords:
            return Response(
                {
                    "status": "error",
                    "message": "El archivo de palabras clave está vacío o no se pudo cargar.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        logger.info("Página de CABI cargada exitosamente.")
        scraping_exitoso = False
        base_domain = "https://www.cabidigitallibrary.org"
        visited_urls = set()

        try:
            with open("cookies.pkl", "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
        except FileNotFoundError:
            logger.info("No se encontraron cookies guardadas.")

        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#onetrust-pc-btn-handler")
                )
            )
            driver.execute_script("arguments[0].click();", cookie_button)
        except Exception:
            logger.info("El botón de 'Aceptar Cookies' no apareció o no fue clicable.")
        try:
            preferences_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#accept-recommended-btn-handler")
                )
            )
            driver.execute_script("arguments[0].click();", preferences_button)

        except Exception:
            logger.info(
                "El botón de 'Guardar preferencias' no apareció o no fue clicable."
            )

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")
            try:
                driver.get(url)
                time.sleep(random.uniform(6, 10))

                search_input = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "#AllFieldb117445f-c250-4d14-a8d9-7c66d5b6a4800",
                        )
                    )
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))

                search_input.submit()
                logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                continue

            visited_counts =0
            max_visits = 50
            
            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.rlist li"))
                    )
                    logger.info("Resultados encontrados en la página.")
                    time.sleep(random.uniform(1, 3))

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("ul.rlist li")
                    if not items:
                        logger.warning(
                            f"No se encontraron resultados para la palabra clave: {keyword}"
                        )
                        break
                    
                    for item in items:
                        if visited_counts>=max_visits:
                            break
                        link = item.find("a")
                        if link and "href" in link.attrs:
                            href = link["href"]
                            if href.startswith("/doi/10.1079/cabicompendium"):
                                absolut_href = f"{base_domain}{href}"
                                driver.get(absolut_href)
                                visited_urls.add(absolut_href)
                                
                                WebDriverWait(driver, 60).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                                )
                                time.sleep(random.uniform(6, 10))
                                soup = BeautifulSoup(driver.page_source, "html.parser")
                                

                                abstracts = soup.select_one("#abstracts")
                                body = soup.select_one("#bodymatter>.core-container")
                                abstract_html = abstracts.prettify() if abstracts else "<p>No abstract found</p>"
                                body_html = body.prettify() if body else "<p>Body not found</p>"
                                nombre_cientifico = "No encontrado"
                                hospedantes = "No encontrado"
                                distribucion = "No encontrado"
                                if body:
                                    species_section = soup.select_one('section[data-type="taxonomicTree"]')
                                    if species_section:
                                        scientific_name_element = species_section.select_one('div[role="listitem"] dt:-soup-contains("Species") + dd')
                                        if scientific_name_element and scientific_name_element.text:
                                            nombre_cientifico = scientific_name_element.get_text(strip=True)

                                    hospedantes_section = soup.select_one('section[data-type="hostPlants"] tbody')
                                    if hospedantes_section:
                                        hospedantes_list = [row.select_one("td").get_text(strip=True) for row in hospedantes_section.select("tr") if row.select_one("td")]
                                        hospedantes = ", ".join(hospedantes_list) if hospedantes_list else "No encontrado"

                                    distribucion_section = soup.select_one('section[data-type="distributionDatabaseTable"] tbody')
                                    if distribucion_section:
                                        distribucion_list = distribucion_section.select("tr")
                                        if distribucion_list:
                                            distribucion = ", ".join([
                                                row.select_one("td.country").get_text(strip=True)
                                                for row in distribucion_list
                                                if row.select_one("td.country") and len(row.select("td")) > 1 and row.select("td")[1] and row.select("td")[1].get_text(strip=True) == "Present"
                                            ])
                                    content_accumulated = f"{abstract_html}\n\n\n{body_html}"
                                    content_accumulated += "-" * 100 + "\n\n"
                                    content_accumulated += f"\n\n🔬 Nombre científico: {nombre_cientifico}"
                                    content_accumulated += f"\n🌍 Distribución: {distribucion}"
                                    content_accumulated += f"\n🦠 Hospedantes: {hospedantes}"

                                    print(f"✅ Página procesada y guardada: {absolut_href}")
                                    if content_accumulated:
                                        print(f"🔬 Nombre científico: {nombre_cientifico}")
                                        print(f"🌍 Distribución: {distribucion}")
                                        print(f"🦠 Hospedantes: {hospedantes}")
                                        object_id = save_to_mongo("cabi_scraper", content_accumulated, absolut_href, url,nombre_cientifico,distribucion,hospedantes)
                                        object_ids.append(object_id)
                                        total_scraped_links += 1
                                        logger.info(f"📂 Noticia guardada en `cabi_scraper` con object_id: {object_id}")
                                        


                                        scraping_exitoso = True
                                        
                                visited_counts+=1
                                driver.back()
                                WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "ul.rlist li")
                                    )
                                )
                                time.sleep(random.uniform(3, 6))
                            else:
                                non_scraped_urls.append(href)
                    if visited_counts >= max_visits:
                        logger.info("🔴 Se alcanzó el límite de 5 enlaces visitados. No se paginará más.")
                        break
                    try:
                        next_page_button = driver.find_element(
                            By.CSS_SELECTOR,
                            ".pagination__btn.pagination__btn--next.icon-arrow_r",
                        )
                        next_page_link = next_page_button.get_attribute("href")

                        if next_page_link:
                            logger.info(
                                f"Yendo a la siguiente página: {next_page_link}"
                            )
                            driver.get(next_page_link)
                        else:
                            logger.info(
                                "No hay más páginas disponibles. Finalizando búsqueda para esta palabra clave."
                            )
                            break
                    except NoSuchElementException:
                        logger.info(
                            "No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave."
                        )
                        driver.get(url)
                        break
                except TimeoutException:
                    logger.warning(
                        f"No se encontraron resultados para '{keyword}' después de esperar."
                    )
                    break

        if scraping_exitoso:
            logger.info(f"🚀 Object IDs recopilados para procesamiento: {object_ids}") 
            all_scraper = (
            f"Total enlaces scrapeados: {total_scraped_links}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
            )
            
            response = process_scraper_data_v2(all_scraper, url, sobrenombre)
            return response
        
    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return {
            "status": "failed",
            "url": url,
            "message": "La página está tardando demasiado en responder. Verifique si la URL es correcta o intente nuevamente más tarde."
        }

    except ConnectionError:
        logger.error("Error de conexión a la URL.")
        return {
            "status": "failed",
            "url": url,
            "message": "No se pudo conectar a la página web."
        }

    except Exception as e:
        logger.error(f"Error al procesar datos del scraper: {str(e)}")
        return {
            "status": "failed",
            "url": url,
            "message": f"Ocurrió un error al procesar los datos: {str(e)}"
        }

    finally:
        driver.quit()
        logger.info("Navegador cerrado")
