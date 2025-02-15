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
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
)
from rest_framework.response import Response
from rest_framework import status
from ..credentials import login_cabi_scienceconnect
import ollama
import json
import re
from datetime import datetime
from django.db import IntegrityError

from ...models.scraperURL import Species, ScraperURL
logger = get_logger("scraper")

def text_to_json(content, source_url, url):
    prompt = f"""
    Organiza el siguiente contenido en el formato JSON especificado.
    
    **Contenido:**
    {content}

    **Estructura esperada en JSON:**
    {{
      "nombre_cientifico": "",
      "nombres_comunes": "",
      "sinonimos": "",
      "descripcion_invasividad": "",
      "distribucion": "",
      "impacto": {{
        "Económico": "",
        "Ambiental": "",
        "Social": ""
      }},
      "habitat": "",
      "ciclo_vida": "",
      "reproduccion": "",
      "hospedantes": "",
      "sintomas": "",
      "organos_afectados": "",
      "condiciones_ambientales": "",
      "prevencion_control": {{
        "Prevención": "",
        "Control": ""
      }},
      "usos": "",
      "url": "{source_url}",
      "hora": "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
      "fuente": "{url}",
      "frecuencia": "Mensual"
    }}

    **Instrucciones:**
    1. Extrae el nombre científico y los nombres comunes de la especie.
    2. Lista los sinónimos científicos si están disponibles.
    3. Proporciona una descripción de la invasividad de la especie.
    4. Identifica los países o regiones donde está distribuida.
    5. Extrae información sobre impacto económico, ambiental y social.
    6. Describe el hábitat donde se encuentra.
    7. Explica el ciclo de vida y los métodos de reproducción.
    8. Lista los hospedantes afectados por la especie.
    9. Describe los síntomas y los órganos afectados en los hospedantes.
    10. Extrae las condiciones ambientales clave como temperatura, humedad y precipitación.
    11. Extrae información sobre métodos de prevención y control.
    12. Lista los usos conocidos de la especie.
    13. Usa la hora actual para completar el campo "hora".
    14. Usa "Mensual" como frecuencia de escrapeo.
    15. Si no encuentras información, usa `""`.

    Devuelve solo el JSON con los datos extraídos, sin texto adicional.
    """

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response["message"]["content"]

    match = re.search(r"\{.*\}", raw_output, re.DOTALL)

    if match:
        clean_output = match.group(0)  
        try:
            json_output = json.loads(clean_output)
            print("✅ JSON convertido correctamente:", json_output)
            return json_output  
        except json.JSONDecodeError as e:
            print("❌ Error al convertir a JSON:", e)
            print("🚨 JSON detectado pero inválido:", clean_output)
            return None
    else:
        print("❌ No se encontró JSON válido en la respuesta de Ollama.")
        print("🚨 Respuesta original:", raw_output)
        return None

def scraper_cabi_digital(url, sobrenombre):
    driver = initialize_driver()
    species_urls = []  # Definir lista antes de usarla

    try:
        if login_cabi_scienceconnect(driver):
            print("Login completado, continuando con el scraping...")
    except:
        logger.error("No se encontró el login")

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
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
                        logger.warning(f"No se encontraron resultados para la palabra clave: {keyword}")
                        break

                    for item in items:
                        link = item.find("a")
                        if link and "href" in link.attrs:
                            href = link["href"]
                            if href.startswith("/doi/10.1079/cabicompendium"):
                                absolut_href = f"{base_domain}{href}"

                                try:
                                    driver.get(absolut_href)
                                    visited_urls.add(absolut_href)

                                    WebDriverWait(driver, 60).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                                    )
                                    time.sleep(random.uniform(6, 10))
                                    soup = BeautifulSoup(driver.page_source, "html.parser")

                                    abstracts = soup.select_one("#abstracts")
                                    body = soup.select_one("#bodymatter>.core-container")
                                    abstract_text = abstracts.get_text(strip=True) if abstracts else "No abstract found"
                                    body_text = body.get_text(strip=True) if body else "No body found"

                                    if abstract_text or body_text:
                                        content_accumulated = f"URL:{absolut_href} \nTexto: {abstract_text}\n\n\n{body_text}"
                                        content_accumulated += "-" * 100 + "\n\n"

                                        print(f"Página procesada y guardada: {absolut_href}")

                                        if content_accumulated:
                                            structured_data = text_to_json(content_accumulated, absolut_href, url)
                                            print("📌 Datos que se guardarán en PostgreSQL:", structured_data)

                                            if structured_data:
                                                try:
                                                    with transaction.atomic():
                                                        scraper_source, _ = ScraperURL.objects.get_or_create(url=url)
                                                        species_obj, created = Species.objects.update_or_create(
                                                            source_url=absolut_href,
                                                            defaults={
                                                                "scientific_name": structured_data.get("nombre_cientifico", ""),
                                                                "common_names": structured_data.get("nombres_comunes", ""),
                                                                "synonyms": structured_data.get("sinonimos", ""),
                                                                "invasiveness_description": structured_data.get("descripcion_invasividad", ""),
                                                                "distribution": structured_data.get("distribucion", ""),
                                                                "impact": structured_data.get("impacto", {}),
                                                                "habitat": structured_data.get("habitat", ""),
                                                                "life_cycle": structured_data.get("ciclo_vida", ""),
                                                                "reproduction": structured_data.get("reproduccion", ""),
                                                                "hosts": structured_data.get("hospedantes", ""),
                                                                "symptoms": structured_data.get("sintomas", ""),
                                                                "affected_organs": structured_data.get("organos_afectados", ""),
                                                                "environmental_conditions": structured_data.get("condiciones_ambientales", ""),
                                                                "prevention_control": structured_data.get("prevencion_control", {}),
                                                                "uses": structured_data.get("usos", ""),
                                                                "scraper_source": scraper_source
                                                            }
                                                        )

                                                        species_urls.append(absolut_href)
                                                        logger.info(f"Especie guardada en PostgreSQL con URL: {absolut_href}")

                                                        scraping_exitoso = True
                                                except IntegrityError:
                                                    logger.warning(f"La especie '{structured_data.get('nombre_cientifico', '')}' ya existe en la base de datos.")
                                                    continue

                                except Exception as e:
                                    logger.error(f"Error al procesar la URL {absolut_href}: {e}")

                                finally:
                                    try:
                                        driver.back()
                                        WebDriverWait(driver, 30).until(
                                            EC.presence_of_element_located(
                                                (By.CSS_SELECTOR, "ul.rlist li")
                                            )
                                        )
                                        time.sleep(random.uniform(3, 6))
                                    except Exception as e:
                                        logger.error(f"Error al volver atrás en la navegación: {e}")

                    try:
                        next_page_button = driver.find_element(
                            By.CSS_SELECTOR,
                            ".pagination__btn.pagination__btn--next.icon-arrow_r",
                        )
                        next_page_link = next_page_button.get_attribute("href")

                        if next_page_link:
                            logger.info(f"Yendo a la siguiente página: {next_page_link}")
                            driver.get(next_page_link)
                        else:
                            logger.info("No hay más páginas disponibles. Finalizando búsqueda para esta palabra clave.")
                            contin
                    except NoSuchElementException:
                        logger.info("No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave.")
                        driver.get(url)
                        continue
                except TimeoutException:
                    logger.warning(f"No se encontraron resultados para '{keyword}' después de esperar.")
                    break

        if scraping_exitoso:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Etiquetas": ["planta", "plaga"],
                    "Mensaje": "Los datos han sido scrapeados correctamente.",
                    "Urls_guardadas": species_urls
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos relevantes en el scraping.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )
    except Exception as e:
        logger.error(f"Error al procesar datos del scraper: {str(e)}")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "Ocurrió un error al procesar los datos.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        if driver:
            driver.quit()
            logger.info("Navegador cerrado")
