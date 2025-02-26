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
    process_scraper_data_v2,
    get_random_user_agent
)
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId
from ...models.scraperURL import Species,ScraperURL
import ollama
import json
import requests

logger = get_logger("scraper")

def text_to_json(content, source_url, url):
    print("📩 Enviando a Ollama para conversión:", len(content), "caracteres")

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
        model="llama3:70b",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response["message"]["content"]
    print("Respuesta completa del modelo:", raw_output)

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
def procesar_y_guardar_en_postgres(object_id):
    try:
        print(f"🔍 Procesando Object ID: {object_id}")  # Asegurar que entra aquí

        client = MongoClient("mongodb://localhost:27017/")
        db = client["scrapping-can"]
        fs = gridfs.GridFS(db)

        # Obtener contenido desde MongoDB
        file_data = fs.get(ObjectId(object_id))  
        content = file_data.read().decode("utf-8")  
        source_url = file_data.source_url  
        url = file_data.url  

        print(f"📄 Obteniendo contenido de MongoDB (ID: {object_id})...")

        # Llamar a la función de conversión para generar el JSON estructurado
        structured_data = text_to_json(content, source_url, url)

        if structured_data:
            print("✅ JSON generado correctamente, guardando en PostgreSQL...")

            # Obtener o crear la fuente del scraping
            scraper_source, _ = ScraperURL.objects.get_or_create(url=url)

            # Guardar en PostgreSQL usando el modelo Django
            species_obj = Species.objects.create(
                scientific_name=structured_data.get("nombre_cientifico", ""),
                common_names=structured_data.get("nombres_comunes", ""),
                synonyms=structured_data.get("sinonimos", ""),
                invasiveness_description=structured_data.get("descripcion_invasividad", ""),
                distribution=structured_data.get("distribucion", ""),
                impact=json.dumps(structured_data.get("impacto", {})),  # Convertir a JSON si es un dict
                habitat=structured_data.get("habitat", ""),
                life_cycle=structured_data.get("ciclo_vida", ""),
                reproduction=structured_data.get("reproduccion", ""),
                hosts=structured_data.get("hospedantes", ""),
                symptoms=structured_data.get("sintomas", ""),
                affected_organs=structured_data.get("organos_afectados", ""),
                environmental_conditions=structured_data.get("condiciones_ambientales", ""),
                prevention_control=json.dumps(structured_data.get("prevencion_control", {})),  # Convertir a JSON
                uses=structured_data.get("usos", ""),
                source_url=source_url,
                scraper_source=scraper_source
            )

            print(f"✅ Especie guardada en PostgreSQL con URL: {source_url}")
            return species_obj.id  # Devolver el ID de la especie guardada en PostgreSQL

        else:
            print("❌ Error en la conversión a JSON.")
            return None

    except Exception as e:
        print(f"🚨 Error al obtener contenido desde MongoDB o guardar en PostgreSQL: {e}")
        return None


# 📌 Función para procesar automáticamente todos los ObjectId guardados
def procesar_todos_los_scrapeos_y_guardar(object_ids):
    print(f"🔄 Procesando {len(object_ids)} documentos y guardando en PostgreSQL...")
    for obj_id in object_ids:
        procesar_y_guardar_en_postgres(obj_id)
    print("✅ Procesamiento completado.")


def scraper_biota_nz(url, sobrenombre):
    driver = initialize_driver()
    base_domain = "https://biotanz.landcareresearch.co.nz"
    species_urls = []  
    total_scraped_links = 0
    collection, fs = connect_to_mongo()
    object_ids = []
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

        logger.info("Página de BIOTA NZ cargada exitosamente.")
        scraping_exitoso = False

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
                        logger.warning(f"No se encontraron resultados para la palabra clave: {keyword}")
                        break
                    visited_counts =0
                    max_visits = 5
                    for item in items:
                        if visited_counts>=max_visits:
                            break
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
                                link_soup = BeautifulSoup(response.content, "html.parser")
                                section_head = link_soup.select_one("div#detail-page div#section-head h2")
                                title_text = section_head.get_text(strip=True) if section_head else ""

                                section_body = link_soup.select_one("div#detail-page div#section-body")
                                sections_text = ""

                                if section_body:
                                    sections = section_body.find_all("div", id=lambda x: x and x.startswith("section-"))
                                    sections_text = "\n".join(section.get_text(strip=True) for section in sections)

                                content_accumulated = f"Nombre Científico: {title_text}\n{sections_text}"
                                print("📌 Contenido extraído antes de pasar a Ollama:\n", content_accumulated)

                                if content_accumulated:
                                    object_id = fs.put(
                                        content_accumulated.encode("utf-8"),
                                        source_url=full_url,
                                        scraping_date=datetime.now(),
                                        Etiquetas=["planta", "plaga"],
                                        contenido=content_accumulated,
                                        url=url
                                    )
                                    total_scraped_links += 1
                                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                    object_ids.append(object_id) 
                                    existing_versions = list(fs.find({"source_url": full_url}).sort("scraping_date", -1))
                                    if len(existing_versions) > 1:
                                        oldest_version = existing_versions[-1]
                                            
                                            # ✅ Acceder al `_id` correctamente
                                        file_id = oldest_version._id  # Esto obtiene el ID correcto
                                        fs.delete(file_id)  # Eliminar la versión más antigua
                                        logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")  # Log correcto
                                        scraping_exitoso = True

                                        
                                visited_counts+=1
                                if visited_counts >= max_visits:
                                    logger.info("🔴 Se alcanzó el límite de 5 enlaces visitados. No se paginará más.")
                                    break
                    try:
                        next_page = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'paging-hyperlink') and contains(text(), 'Next')]"))
                        )
                        driver.execute_script("arguments[0].click();", next_page)
                        time.sleep(random.uniform(6, 10))
                    except Exception:
                        logger.info("No hay más páginas disponibles.")
                        break
                except TimeoutException:
                    logger.warning(f"No se encontraron resultados para '{keyword}' después de esperar.")
                    break

        if scraping_exitoso:
            procesar_todos_los_scrapeos_y_guardar(object_ids)
            all_scraper="listo"

            response = process_scraper_data_v2(all_scraper, url, sobrenombre)
            return response
        

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