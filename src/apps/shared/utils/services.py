from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.utils.scrapers import SCRAPER_FUNCTIONS
from src.apps.shared.models.scraperURL import Species, ReportComparison
import logging
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime
import requests
import json
import re
from django.db import transaction
logger = logging.getLogger(__name__)


class WebScraperService:
    def scraper_expired_urls(self):
        from src.apps.shared.utils.tasks import scraper_url_task

        urls = ScraperURL.objects.filter(is_active=True)

        for scraper_url in urls:
            if scraper_url.is_time_expired():
                try:
                    scraper_url_task.delay(scraper_url.url)

                    logger.info(f"Tarea encolada para URL: {scraper_url.url}")
                except Exception as e:
                    logger.error(
                        f"Error al encolar scraping para {scraper_url.url}: {str(e)}"
                    )

    def scraper_one_url(self, url):
        try:
            scraper_url = ScraperURL.objects.get(url=url)
            mode_scrapeo = scraper_url.mode_scrapeo
            scraper_function = SCRAPER_FUNCTIONS.get(mode_scrapeo)

            if not scraper_function:
                logger.error(f"Modo de scrapeo no reconocido para URL: {url}")
                return {"error": f"Modo de scrapeo no reconocido para URL: {url}"}

            kwargs = {"url": url, "sobrenombre": scraper_url.sobrenombre}
            if mode_scrapeo == 7:
                parameters = scraper_url.parameters or {}
                kwargs["start_page"] = parameters.get("start_page", 1)
                kwargs["end_page"] = parameters.get("end_page", None)

            response = scraper_function(**kwargs)

            if isinstance(response, dict):
                logger.info(f"Scraping completado para URL: {url}")
                return response
            else:
                logger.error(f"Respuesta no serializable para URL: {url}")
                return {"error": f"Respuesta no serializable para URL: {url}"}
        except ScraperURL.DoesNotExist:
            logger.error(f"No se encontraron parámetros para la URL: {url}")
            return {"error": f"No se encontraron parámetros para la URL: {url}"}
        except Exception as e:
            logger.error(f"Error durante el scraping para {url}: {str(e)}")
            return {"error": f"Error durante el scraping para {url}: {str(e)}"}


class ScraperService:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["fs.files"]

    def extract_and_save_species(self):

        documents = self.collection.find({"processed": {"$ne": True}})

        for doc in documents:
            content = doc.get("contenido", "")
            source_url = doc.get("source_url", "")
            url = doc.get("url", "")

            if not content:
                logger.warning(f"Documento {doc['_id']} no tiene contenido.")
                continue

            structured_data = self.text_to_json(content, source_url, url)

            if structured_data:
                self.save_species_to_postgres(
                    structured_data, source_url, url
                )

                self.collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
                )
                logger.info(f"Procesado y guardado en PostgreSQL: {doc['_id']}")



    def text_to_json(self, content, source_url, url):
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
        "fuente": "{url}"
        }}

        **Instrucciones:**
        Devuelve solo el JSON. **No agregues texto antes o después del JSON.**
        2. **No uses comillas triples , ni bloques de código (`'''`).**

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
            Devuelve solo el JSON con los datos extraídos, sin texto adicional.
        """

        response = requests.post(
            "http://127.0.0.1:11434/api/chat",
            json={"model": "llama3:8b", "messages": [{"role": "user", "content": prompt}]},
            stream=True  
        )

        full_response = ""

        for line in response.iter_lines():
            if line:
                try:
                    json_line = json.loads(line.decode("utf-8"))
                    full_response += json_line.get("message", {}).get("content", "")
                except json.JSONDecodeError:
                    print("❌ Error al decodificar JSON:", line)

        print("🔍 Respuesta completa de Ollama:", full_response)

        match = re.search(r"\{.*\}", full_response, re.DOTALL)
        if match:
            json_text = match.group(0) 
            try:
                parsed_json = json.loads(json_text)
                return parsed_json
            except json.JSONDecodeError as e:
                print(f"❌ Error al convertir JSON después de limpiar: {str(e)}")
                print("📌 JSON detectado:", json_text)
                return None
        else:
            print("⚠️ No se encontró un JSON válido en la respuesta de Ollama.")
            return None



    def save_species_to_postgres(self, structured_data, source_url, url):

        try:
            print(f"Intentando guardar en PostgreSQL: {structured_data}")
            scraper_source, created = ScraperURL.objects.get_or_create(url=url, defaults={"Sobrenombre":"Fuente desconocida"})
            species_obj = Species.objects.create(
                scientific_name=structured_data.get("nombre_cientifico", ""),
                common_names=structured_data.get("nombres_comunes", ""),
                synonyms=structured_data.get("sinonimos", ""),
                invasiveness_description=structured_data.get(
                    "descripcion_invasividad", ""
                ),
                distribution=structured_data.get("distribucion", ""),
                impact=structured_data.get("impacto", {}),
                habitat=structured_data.get("habitat", ""),
                life_cycle=structured_data.get("ciclo_vida", ""),
                reproduction=structured_data.get("reproduccion", ""),
                hosts=structured_data.get("hospedantes", ""),
                symptoms=structured_data.get("sintomas", ""),
                affected_organs=structured_data.get("organos_afectados", ""),
                environmental_conditions=structured_data.get(
                    "condiciones_ambientales", ""
                ),
                prevention_control=structured_data.get("prevencion_control", {}),
                uses=structured_data.get("usos", ""),
                source_url=source_url,
                scraper_source=scraper_source,
            )
            logger.info(f"Especie guardada en PostgreSQL con ID: {species_obj.id}")
        except Exception as e:
            logger.error(f"Error al guardar en PostgreSQL: {str(e)}")
class ScraperComparisonService:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["collection"]  
    def compare_scraped_content(self, url):

        documents = list(self.collection.find({"url": url}).sort("scraping_date", -1))

        if len(documents) < 2:
            logger.info(f"No hay suficientes versiones de la URL {url} para comparar.")
            return {"status": "no_comparison", "message": "Menos de dos registros encontrados."}

        doc1, doc2 = documents[:2]  
        content1 = doc1.get("contenido", "")
        content2 = doc2.get("contenido", "")

        object_id1 = str(doc1["_id"])  
        object_id2 = str(doc2["_id"])  

        if not content1 or not content2:
            logger.warning(f"Uno de los documentos ({object_id1}, {object_id2}) no tiene contenido.")
            return {"status": "missing_content", "message": "Uno de los registros no tiene contenido."}

        existing_report = ReportComparison.objects.filter(scraper_source__url=url).first()

        if existing_report:
            if existing_report.object_id1 == object_id1 and existing_report.object_id2 == object_id2:
                logger.info(f"La comparación entre {object_id1} y {object_id2} ya existe y no ha cambiado.")
                return {"status": "duplicate", "message": "La comparación ya fue realizada anteriormente."}

            logger.info(f"Detectado cambio en ObjectId. Reprocesando comparación para {url}.")
        
        comparison_result = self.generate_comparison_with_ollama(content1, content2, url, object_id1, object_id2)

        if comparison_result:
            self.save_or_update_comparison_to_postgres(url, object_id1, object_id2, comparison_result)

        return comparison_result

    def generate_comparison_with_ollama(self, content1, content2, url, object_id1, object_id2):

        prompt = f"""
        Compara los siguientes dos reportes extraídos de la misma URL y genera un resumen de los cambios:

        **URL:** {url}
        
        **Reporte 1 (ObjectId: {object_id1}):**
        {content1}

        **Reporte 2 (ObjectId: {object_id2}):**
        {content2}

        **Instrucciones para el análisis:**
        1. Identifica las diferencias clave entre los dos reportes.
        2. Especifica cuánta información nueva se agregó en el segundo reporte.
        3. Muestra qué se eliminó o modificó en comparación con el primer reporte.
        4. Indica si la estructura general del reporte ha cambiado.
        5. Devuelve un resumen en formato JSON con los cambios encontrados.

        **Estructura esperada en JSON:**
        {{
            "info_agregada": "",
            "info_eliminada": "",
            "info_modificada": "",
            "estructura_cambio": false
        }}

        Devuelve solo el JSON, sin texto adicional.
        """

        try:
            response = requests.post(
                "http://127.0.0.1:11434/api/chat",
                json={"model": "llama3:8b", "messages": [{"role": "user", "content": prompt}]},
                timeout=30,  
                stream=True
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la solicitud a Ollama: {str(e)}")
            return None

        full_response = ""

        for line in response.iter_lines():
            if line:
                try:
                    json_line = json.loads(line.decode("utf-8"))
                    full_response += json_line.get("message", {}).get("content", "")
                except json.JSONDecodeError:
                    logger.error("Error al decodificar JSON:", line)

        logger.info("🔍 Respuesta completa de Ollama:", full_response)

        match = re.search(r"\{.*\}", full_response, re.DOTALL)
        if match:
            json_text = match.group(0)
            try:
                parsed_json = json.loads(json_text)
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error al convertir JSON después de limpiar: {str(e)}")
                logger.error("📌 JSON detectado:", json_text)
                return None
        else:
            logger.warning("⚠️ No se encontró un JSON válido en la respuesta de Ollama.")
            return None

    def save_or_update_comparison_to_postgres(self, url, object_id1, object_id2, comparison_result):

        try:
            scraper_source, created = ScraperURL.objects.get_or_create(url=url, defaults={"sobrenombre": "Fuente desconocida"})

            with transaction.atomic(): 
                report, created = ReportComparison.objects.update_or_create(
                    scraper_source=scraper_source,
                    defaults={
                        "object_id1": object_id1,
                        "object_id2": object_id2,
                        "info_agregada": comparison_result.get("info_agregada", ""),
                        "info_eliminada": comparison_result.get("info_eliminada", ""),
                        "info_modificada": comparison_result.get("info_modificada", ""),
                        "estructura_cambio": comparison_result.get("estructura_cambio", False)
                    }
                )
                action = "creado" if created else "actualizado"
                logger.info(f"Reporte de comparación {action} en PostgreSQL con ID: {report.id}")
        except Exception as e:
            logger.error(f"Error al guardar o actualizar comparación en PostgreSQL: {str(e)}")