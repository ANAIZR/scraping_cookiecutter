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
from bs4 import NavigableString
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
    content_accumulated =""

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
            max_visits = 5
            
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
                                common_names = "No encontrado"
                                synonyms = "No encontrado"
                                invasiveness_description = "No encontrado"
                                impact = "No encontrado"
                                habitat = "No encontrado"
                                reproduction = "No encontrado"
                                symptoms = "No encontrado"
                                affected_organs = "No encontrado"
                                environmental_conditions = "No encontrado"

                                if body:
                                    # 🦠 Nombre científico
                                    species_section = soup.select_one('section[data-type="taxonomicTree"]')
                                    if species_section:
                                        scientific_name_element = species_section.select_one('div[role="listitem"] dt:-soup-contains("Species") + dd')
                                        nombre_cientifico = scientific_name_element.get_text(strip=True) if scientific_name_element else "No encontrado"

                                    # 🌱 Hospedantes
                                    hospedantes_section = soup.select_one('section[data-type="hostPlants"] tbody')
                                    if hospedantes_section:
                                        hospedantes_list = [row.select_one("td").get_text(strip=True) for row in hospedantes_section.select("tr") if row.select_one("td")]
                                        hospedantes = ", ".join(hospedantes_list) if hospedantes_list else "No encontrado"

                                    # 🌍 Distribución
                                    distribucion_section = soup.select_one('section[data-type="distributionDatabaseTable"] tbody')
                                    if distribucion_section:
                                        distribucion_list = distribucion_section.select("tr")
                                        if distribucion_list:
                                            distribucion = ", ".join([
                                                row.select_one("td.country").get_text(strip=True)
                                                for row in distribucion_list
                                                if row.select_one("td.country") and len(row.select("td")) > 1 and row.select("td")[1].get_text(strip=True) == "Present"
                                            ]) if distribucion_list else "No encontrado"

                                    # 📌 Nombres comunes
                                    common_names_section = soup.select_one('section[data-type="identity"]')
                                    if common_names_section:
                                        common_names_list = []
                                        for dt_text in ["International Common Names", "Local Common Names"]:
                                            dt_element = common_names_section.find('dt', string=lambda text: dt_text in text if text else False)
                                            if dt_element:
                                                dds = dt_element.find_all_next('dd', limit=3)
                                                common_names_list.extend(dd.get_text(strip=True) for dd in dds if dd)
                                        common_names = ", ".join(common_names_list) if common_names_list else "No encontrado"

                                    # 🔬 Sinónimos
                                    other_scientific_names_section = soup.select_one('section[data-type="identity"]')
                                    if other_scientific_names_section:
                                        synonyms_list = []
                                        other_scientific_names_dt = other_scientific_names_section.find('dt', string="Other Scientific Names")
                                        if other_scientific_names_dt:
                                            synonyms_list = [dd.get_text(strip=True) for dd in other_scientific_names_dt.find_all_next('dd') if dd.text.strip()]
                                        synonyms = ", ".join(synonyms_list) if synonyms_list else "No encontrado"

                                    # 🏹 Invasividad
                                    description_section = soup.select_one('section[data-type="description"]')
                                    if description_section:
                                        paragraph = description_section.select_one('div[role="paragraph"]')
                                        invasiveness_description = paragraph.get_text(strip=True) if paragraph else "No encontrado"

                                    # ⚠ Impacto
                                    bio_section = soup.select_one('section[data-type="biologyAndEcology"]')

                                    if bio_section:
                                        paragraphs = bio_section.find_all('div', {"role": "paragraph"})
                                        
                                        # Extraer solo texto puro, eliminando cualquier etiqueta HTML
                                        reproduction = []
                                        
                                        for p in paragraphs:
                                            for element in p.descendants:  # Recorre todo el contenido del párrafo
                                                if isinstance(element, NavigableString):  # Solo guarda texto real
                                                    reproduction.append(element.strip())

                                        # Unir todo en un solo string limpio
                                        reproduction = " ".join(reproduction) if reproduction else "No encontrado"
                                    else:
                                        reproduction = "No encontrado"
                                    # 🌳 Hábitat
                                    env_section = soup.select_one('section[data-type="environments"]')
                                    if env_section:
                                        habitats = [row.select("td")[2].get_text(strip=True) for row in env_section.select('tbody tr') if len(row.select("td")) >= 3]
                                        habitat = ", ".join(habitats) if habitats else "No encontrado"

                                    # 🔁 Reproducción
                                    bio_section = soup.select_one('section[data-type="biologyAndEcology"]')
                                    if bio_section:
                                        reproduction = " ".join([p.get_text(" ", strip=True) for p in bio_section.find_all('div', {"role": "paragraph"})])

                                        

                                    # 🤒 Síntomas
                                    symptoms_section = soup.select_one('section[data-type="symptoms"]')
                                    if symptoms_section:
                                        paragraph = symptoms_section.select_one('div[role="paragraph"]')
                                        symptoms = paragraph.get_text(" ", strip=True) if paragraph else "No encontrado"

                                    # 🏥 Órganos afectados
                                    host_plants_section = soup.select_one('section[data-type="hostPlants"]')
                                    if host_plants_section:
                                        first_row = host_plants_section.select_one('tbody tr')
                                        affected_organs = ", ".join([td.get_text(strip=True) for td in first_row.find_all('td')]) if first_row else "No encontrado"

                                    # 🌿 Condiciones ambientales


                                    ambiental_section = soup.select_one('section[data-type="biologyAndEcology"]')

                                    if ambiental_section:
                                        # Extraer todo el texto sin etiquetas, asegurando que no sea un objeto HTML
                                        environmental_conditions = ambiental_section.get_text(separator=" ", strip=True)
                                    else:
                                        environmental_conditions = "No encontrado"

                                    content_accumulated=""          
                                    content_accumulated += f"\n\n🔬 Nombre científico: {nombre_cientifico}"
                                    content_accumulated += f"\n🌍 Distribución: {distribucion}"
                                    content_accumulated += f"\n🦠 Hospedantes: {hospedantes}"
                                    content_accumulated += f"\n Nombres comunes: {common_names}"
                                    content_accumulated += f"\n Sinonimos: {synonyms}"
                                    content_accumulated += f"\n Invasion: {invasiveness_description}"
                                    content_accumulated += f"\n Impacto: {impact}"
                                    content_accumulated += f"\n Habitat: {habitat}"
                                    content_accumulated += f"\n Reproduccion: {reproduction}"
                                    content_accumulated += f"\n Sintomas: {symptoms}"
                                    content_accumulated += f"\n Organos afectados: {affected_organs}"
                                    content_accumulated += f"\n Seccion ambiental: {environmental_conditions}"
                                    print(f"✅ Página procesada y guardada: {absolut_href}")
                                    if content_accumulated:
                                        print(f"🔬 Nombre científico: {nombre_cientifico}")
                                        print(f"🌍 Distribución: {distribucion}")
                                        print(f"🦠 Hospedantes: {hospedantes}")
                                        print(f"🦠 Nombres comunes: {common_names}")
                                        print(f"🦠 Sinonimos : {synonyms}")
                                        print(f"🦠 Descripcion : {invasiveness_description}")
                                        print(f"🦠 Impacto : {impact}")
                                        print(f"🦠 Habitat : {habitat}")
                                        print(f"🦠 Reproduccion : {reproduction}")
                                        print(f"🦠 Sintomas : {symptoms}")
                                        print(f"🦠 Organos afectados : {affected_organs}")
                                        print(f"🦠 Seccion ambiental : {environmental_conditions}")                                        
                                        object_id = save_to_mongo("cabi_scraper", content_accumulated, absolut_href, url,nombre_cientifico,distribucion,hospedantes,common_names, synonyms,invasiveness_description,impact,habitat,reproduction,symptoms,affected_organs,environmental_conditions)
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
