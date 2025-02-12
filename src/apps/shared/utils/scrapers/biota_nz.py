from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (

    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
    get_random_user_agent,
)
from rest_framework.response import Response
from rest_framework import status
from selenium.common.exceptions import TimeoutException
from bson import ObjectId

logger = get_logger("scraper")
import ollama
import json
from datetime import datetime

def text_to_json(content, url):
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
      "url": "{url}",
      "hora": "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
      "fuente": "CABI Digital Library",
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

    Devuelve solo el JSON con los datos extraídos, sin texto adicional.
    """

    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}]
    )

    json_output = response["message"]["content"]

    try:
        return json.loads(json_output)  # Convertir a JSON
    except json.JSONDecodeError:
        print("Error al convertir a JSON")
        return None


def scraper_biota_nz(url, sobrenombre):
    driver = initialize_driver()
    base_domain = "https://biotanz.landcareresearch.co.nz"

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        logger.info(f"Iniciando scraping para URL: {url}")
        collection, fs = connect_to_mongo()

        keywords = load_keywords("plants.txt")
        if not keywords:
            return Response(
                {
                    "status": "error",
                    "message": "El archivo de palabras clave está vacío o no se pudo cargar.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Página de BIOTA NZ cargada exitosamente.")

        scraping_exitoso = False
        object_ids = []
        object_urls = []

        for keyword in keywords:
            logger.info(f"Buscando la palabra clave: {keyword}")

            try:
                driver.get(url)
                time.sleep(random.uniform(6, 10))

                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#query"))
                )
                search_box.clear()
                search_box.send_keys(keyword)
                time.sleep(random.uniform(3, 6))
                search_box.submit()
            except Exception as e:
                logger.error(f"Error al buscar la palabra clave '{keyword}': {e}")
                continue


            while True:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "list-result"))
                    )
                    logger.info(f"Resultados cargados para: {keyword}")
                    time.sleep(random.uniform(1, 3))
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("div.row-separation.specimen-list-item")

                    if not items:
                        logger.warning(
                            f"No se encontraron resultados para la palabra clave: {keyword}"
                        )
                        break

                    for item in items:
                        link_element = item.select_one("div.col-12 > a[href]")
                        if link_element:
                            href = link_element["href"]
                            full_url = f"{base_domain}{href}"
                            logger.info(f"Procesando enlace: {full_url}")
                            response = requests.get(
                                full_url,
                                headers={"User-Agent": get_random_user_agent()},
                                timeout=10  
                            )

                            if response.status_code == 200:
                                link_soup = BeautifulSoup(
                                    response.content, "html.parser"
                                )
                                section_head = link_soup.select_one("div#detail-page div#section-head h2")
                                title_text = section_head.get_text(strip=True) if section_head else ""

                                section_body = link_soup.select_one("div#detail-page div#section-body")
                                sections_html = ""

                                if section_body:
                                    sections = section_body.find_all("div", id=lambda x: x and x.startswith("section-"))
                                    sections_text = "\n".join(section.get_text(strip=True) for section in sections)

                                content_accumulated = f"Nombre Científico: {title_text}\n{sections_text}"

                                if content_accumulated:
                                    structured_data = text_to_json(content_accumulated, full_url)
                                    
                                    if structured_data:
                                        object_id = fs.put(
                                            json.dumps(structured_data, ensure_ascii=False).encode("utf-8"),
                                            metadata={
                                                "url_source": full_url,
                                                "url": url,
                                                "scraping_date": datetime.now(),
                                                "Etiquetas": ["planta", "plaga"],
                                                "contenido": structured_data,
                                            },
                                        )
                                        object_ids.append(object_id)
                                        object_urls.append(full_url)
                                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                                        collection.insert_one(structured_data)

                                        existing_versions = list(
                                            collection.find({"url_source": full_url}).sort("scraping_date", -1)
                                        )

                                        if len(existing_versions) > 2:
                                            oldest_version = existing_versions[-1]
                                            fs.delete(ObjectId(oldest_version["_id"]))
                                            collection.delete_one({"_id": ObjectId(oldest_version["_id"])})
                                            logger.info(
                                                f"Se eliminó la versión más antigua de '{keyword}' con URL '{full_url}' y object_id: {oldest_version['_id']}"
                                            )
                                        scraping_exitoso = True


                    try:
                        next_page = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//a[contains(@class, 'paging-hyperlink') and contains(text(), 'Next')]",
                                )
                            )
                        )
                        driver.execute_script("arguments[0].click();", next_page)
                        time.sleep(random.uniform(6, 10))
                    except Exception:
                        logger.info("No hay más páginas disponibles.")
                        break
                except TimeoutException:
                    logger.warning(
                        f"No se encontraron resultados para '{keyword}' después de esperar."
                    )
                    break

        if scraping_exitoso:

            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Etiquetas": ["planta", "plaga"],
                    "Mensaje": "Los datos han sido scrapeados correctamente.",
                    "Object_Ids": [
                        str(obj_id) for obj_id in object_ids
                    ],  
                    "Urls": object_urls
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
    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "La página está tardando demasiado en responder. Verifique si la URL es correcta o intente nuevamente más tarde.",
            },
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )

    except requests.ConnectionError:
        logger.error("Error de conexión a la URL.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "No se pudo conectar a la página web.",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
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