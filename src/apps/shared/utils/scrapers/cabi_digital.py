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
    connect_to_mongo,
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

logger = get_logger("scraper")
import requests
import json

def text_to_json(content, source_url, url):
    print("📩 Enviando a Ollama para conversión:", len(content), "caracteres")

    prompt = f"""
   Organiza el siguiente contenido en **formato JSON**, pero **cada campo que contenga múltiples valores debe estar separado por comas dentro de un string, en lugar de usar un array JSON**.
    **Cada campo con múltiples valores debe ser un string separado por comas**, en lugar de un array JSON.
    **Las secciones `prevencion_control` e `impacto` deben mantenerse como objetos anidados con sus claves correspondientes.**
    **Si un campo no tiene información, usa `""`.**
    ### **🔹 Reglas de extracción**
    
     - **`impacto`**: Mantén las claves `"Económico"`, `"Ambiental"` y `"Social"`, sin cambiar la estructura.
    - **`prevencion_control`**: Mantén las claves `"Prevención"` y `"Control"`, sin cambiar la estructura.
    - **No omitas información, si no la encuentras, usa `""`.**  
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

     **Instrucciones: EN TODO EL CONTENT BUSCA ESTA INFORMACION**
    1. Extrae los nombres comunes de la especie.
    2. Lista los sinónimos científicos si están disponibles.
    3. Proporciona una descripción de la invasividad de la especie.
    4. Extrae información sobre impacto económico, ambiental y social.
    5. Describe el hábitat donde se encuentra.
    6. Explica el ciclo de vida y los métodos de reproducción.
    7. Describe los síntomas y los órganos afectados en los hospedantes.
    8. Extrae las condiciones ambientales clave como temperatura, humedad y precipitación.
    9. Extrae información sobre métodos de prevención y control.
    10. Lista los usos conocidos de la especie.
    11. Si no encuentras información, usa `""`.

    Devuelve solo el JSON con los datos extraídos, sin texto adicional. NO OMITAS NINGUNA INFORMACION
    """

    api_url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llama3:70b",
        "prompt": prompt,
        "stream": False
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Lanza error si la respuesta no es 200 OK

        json_output = response.json()
        if "response" in json_output:
            raw_response = json_output["response"]
            
            match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if match:
                try:
                    structured_data = json.loads(match.group(0))
                    print("✅ JSON extraído correctamente:", structured_data)
                    return structured_data
                except json.JSONDecodeError as e:
                    print(f"🚨 Error al decodificar JSON: {e}\n🔍 Respuesta de Ollama: {match.group(0)}")
                    return None
            else:
                print("❌ No se encontró un JSON válido en la respuesta de Ollama.")
                return None



    except requests.exceptions.RequestException as e:
        print(f"🚨 Error al conectar con Ollama: {e}")
        return None
def limpiar_datos_json(structured_data):
    campos_lista = ["nombres_comunes", "sinonimos", "hospedantes", "sintomas", "organos_afectados", "usos"]
    for campo in campos_lista:
        if isinstance(structured_data.get(campo, ""), str):
            try:
                structured_data[campo] = json.loads(structured_data[campo].replace("'", '"'))
                logger.warning(f"⚠️ Error al decodificar {campo}. Se asignará una lista vacía.")

            except json.JSONDecodeError:
                structured_data[campo] = []

    campos_dict = ["impacto", "prevencion_control", "condiciones_ambientales"]
    for campo in campos_dict:
        if isinstance(structured_data.get(campo, ""), str):
            try:
                structured_data[campo] = json.loads(structured_data[campo])
            except json.JSONDecodeError:
                structured_data[campo] = {}

    return structured_data
from django.db.models import JSONField

def procesar_y_guardar_en_postgres(object_id):
    try:
        logger.info(f"🔍 Procesando Object ID: {object_id}")

        client = MongoClient("mongodb://localhost:27017/")
        db = client["scrapping-can"]
        fs = gridfs.GridFS(db)

        file_data = fs.get(ObjectId(object_id))  
        content = file_data.read().decode("utf-8")  
        logger.info(f"📄 Contenido extraído desde MongoDB:\n{content[:500]}...") 

        source_url = file_data.source_url  
        url = file_data.url  

        logger.info(f"📄 Obteniendo contenido de MongoDB (ID: {object_id})...")

        structured_data = text_to_json(content, source_url, url)
        logger.info(f"✅ JSON generado por Ollama:\n{structured_data}")

        if structured_data:
            logger.info("✅ JSON generado correctamente, guardando en PostgreSQL...")
            structured_data = limpiar_datos_json(structured_data) 

            scraper_source, _ = ScraperURL.objects.get_or_create(url=url)
            nombre_cientifico = structured_data.get("nombre_cientifico", "").strip()
            distribucion = ", ".join(structured_data.get("distribucion", [])) if isinstance(structured_data.get("distribucion"), list) else structured_data.get("distribucion", "").strip()
            hospedantes = ", ".join(structured_data.get("hospedantes", [])) if isinstance(structured_data.get("hospedantes"), list) else structured_data.get("hospedantes", "").strip()

           

            newspecies_obj, created = NewSpecies.objects.update_or_create(
                source_url=source_url, 
                defaults={  
                    "scientific_name": nombre_cientifico,
                    "common_names": ", ".join(structured_data.get("nombres_comunes", [])) if isinstance(structured_data.get("nombres_comunes"), list) else structured_data.get("nombres_comunes", ""),
                    "synonyms": ", ".join(structured_data.get("sinonimos", [])) if isinstance(structured_data.get("sinonimos"), list) else structured_data.get("sinonimos", ""),
                    "distribution": distribucion,
                    "impact": structured_data.get("impacto", {"Económico": "", "Ambiental": "", "Social": ""}),
                    "habitat": structured_data.get("habitat", ""),
                    "life_cycle": structured_data.get("ciclo_vida", ""),
                    "reproduction": structured_data.get("reproduccion", ""),
                    "hosts": hospedantes,
                    "symptoms": ", ".join(structured_data.get("sintomas", [])) if isinstance(structured_data.get("sintomas"), list) else structured_data.get("sintomas", ""),
                    "affected_organs": ", ".join(structured_data.get("organos_afectados", [])) if isinstance(structured_data.get("organos_afectados"), list) else structured_data.get("organos_afectados", ""),
                    "environmental_conditions": structured_data.get("condiciones_ambientales", {}),
                    "prevention_control": structured_data.get("prevencion_control", {"Prevención": "", "Control": ""}),
                    "uses": ", ".join(structured_data.get("usos", [])) if isinstance(structured_data.get("usos"), list) else structured_data.get("usos", ""),
                    "scraper_source": scraper_source
                }
            )


            if created:
                logger.info(f"✅ Nueva especie creada en PostgreSQL con URL: {source_url}")
            else:
                logger.info(f"🔄 Especie actualizada en PostgreSQL con URL: {source_url}")

            return newspecies_obj.id 

        else:
            logger.error("❌ Error en la conversión a JSON.")
            return None

    except Exception as e:
        logger.warning(f"🚨 Error al obtener contenido desde MongoDB o guardar en PostgreSQL: {e}")
        return None


def procesar_todos_los_scrapeos_y_guardar(object_ids):
    logger.info(f"🔄 Procesando {len(object_ids)} documentos y guardando en PostgreSQL...")
    if not object_ids:
        logger.error("❌ No hay Object IDs para procesar. Verifica el scraping.")
        return
    
    for obj_id in object_ids:
        logger.info(f"📌 Procesando Object ID: {obj_id}")  # Verificar si entra aquí
        try:
            procesar_y_guardar_en_postgres(obj_id)
        except Exception as e:
            print(f"🚨 Error al procesar Object ID {obj_id}: {e}")

    print("✅ Procesamiento finalizado.")

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
            max_visits = 30
            
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
                                        object_id = fs.put(
                                            content_accumulated.encode("utf-8"),
                                            source_url=absolut_href,
                                            scraping_date=datetime.now(),
                                            Etiquetas=["planta", "plaga"],
                                            contenido=content_accumulated,
                                            url=url
                                        )
                                        total_scraped_links += 1
                                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                        object_ids.append(object_id) 
                                        existing_versions = list(fs.find({"source_url": absolut_href}).sort("scraping_date", -1))
                                        if len(existing_versions) > 1:
                                            oldest_version = existing_versions[-1]
                                                
                                            # ✅ Acceder al `_id` correctamente
                                            file_id = oldest_version._id  # Esto obtiene el ID correcto
                                            fs.delete(file_id)  # Eliminar la versión más antigua
                                            logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")  # Log correcto


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
            procesar_todos_los_scrapeos_y_guardar(object_ids)
            
            response = process_scraper_data_v2(all_scraper, url, sobrenombre)
            return response
        
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
    except ConnectionError:
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
        driver.quit()
        logger.info("Navegador cerrado")
