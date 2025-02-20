from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.utils.scrapers import SCRAPER_FUNCTIONS, scraper_pdf
from src.apps.shared.models.scraperURL import Species, ReportComparison
import logging
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime
import requests
import json
import re
import inspect
from django.db import transaction
from itertools import islice
import time
from django.utils import timezone

logger = logging.getLogger(__name__)


class WebScraperService:
    def get_expired_urls(self):
        return ScraperURL.objects.filter(
                is_active=True, 
                fecha_scraper__lt=datetime.now()
            ).values_list("url", flat=True)


    def scraper_one_url(self, url, sobrenombre):
        try:
            scraper_url = ScraperURL.objects.get(url=url)
            mode_scrapeo = scraper_url.mode_scrapeo

            scraper_function = SCRAPER_FUNCTIONS.get(mode_scrapeo)
            if not scraper_function:
                error_msg = f"Modo de scrapeo {mode_scrapeo} no registrado en SCRAPER_FUNCTIONS"
                scraper_url.estado_scrapeo = "fallido"
                scraper_url.error_scrapeo = error_msg
                scraper_url.ultima_fecha_scrapeo = timezone.now().date()
                scraper_url.save()
                logger.error(error_msg)
                return {"error": error_msg}

            if mode_scrapeo == 7:
                parameters = scraper_url.parameters or {}
                start_page = parameters.get("start_page", 1)
                end_page = parameters.get("end_page", None)
                logger.info(f"Procesando PDF: {url}, páginas {start_page} - {end_page}")

                response = scraper_pdf(url, scraper_url.sobrenombre, start_page, end_page)
                if not isinstance(response, dict):
                    error_msg = "Respuesta no serializable en scraper_pdf"
                    scraper_url.estado_scrapeo = "fallido"
                    scraper_url.error_scrapeo = error_msg
                    scraper_url.ultima_fecha_scrapeo = timezone.now().date()
                    scraper_url.save()
                    return {"error": error_msg}

                scraper_url.estado_scrapeo = "exitoso"
                scraper_url.error_scrapeo = ""
                scraper_url.ultima_fecha_scrapeo = timezone.now().date()
                scraper_url.save()
                return response  

            logger.info(f"Ejecutando scraper para {url} con método {mode_scrapeo}")

            params = inspect.signature(scraper_function).parameters
            if len(params) == 2:
                response = scraper_function(url, sobrenombre)
            else:
                response = scraper_function(url)

            # Verificar si el scraping devolvió datos válidos
            if not response or "error" in response:
                scraper_url.estado_scrapeo = "fallido"
                scraper_url.error_scrapeo = response.get("error", "Scraping no devolvió datos válidos.")
            else:
                scraper_url.estado_scrapeo = "exitoso"
                scraper_url.error_scrapeo = ""

            scraper_url.ultima_fecha_scrapeo = timezone.now().date()
            scraper_url.save()
            return response

        except ScraperURL.DoesNotExist:
            error_msg = f"La URL {url} no se encuentra en la base de datos."
            logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Error al ejecutar scraper para {url}: {str(e)}"
            scraper_url.estado_scrapeo = "fallido"
            scraper_url.error_scrapeo = error_msg
            scraper_url.ultima_fecha_scrapeo = timezone.now().date()
            scraper_url.save()
            logger.error(error_msg)
            return {"error": error_msg}






class ScraperService:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["fs.files"]

    def extract_and_save_species(self, url):
        documents = list(self.collection.find({"url": url, "processed": {"$ne": True}}))  

        if not documents:
            logger.info("No hay documentos pendientes de procesar.")
            return

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(self.process_document, documents) 

    def process_document(self, doc):
        content = doc.get("contenido", "")
        source_url = doc.get("source_url", "")

        if not content:
            logger.warning(f"Documento {doc['_id']} no tiene contenido.")
            return

        structured_data = self.text_to_json(content, source_url, doc.get("url", ""))

        if self.datos_son_validos(structured_data): 
            self.save_species_to_postgres(structured_data, source_url, doc.get("url", ""))

            self.collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"processed": True, "processed_at": datetime.utcnow()}}
            )
            logger.info(f"Procesado y guardado en PostgreSQL: {doc['_id']}")
        else:
            logger.warning(f"Datos vacíos para {doc['_id']}, no se guardan en PostgreSQL.")

    def datos_son_validos(self, datos, min_campos=2):


        if not datos or not isinstance(datos, dict):
            return False

        if not datos.get("nombre_cientifico") or not datos["nombre_cientifico"].strip():
            return False  

        campos_con_datos = 0  

        for clave, valor in datos.items():
            if isinstance(valor, list) and valor:  
                campos_con_datos += 1
            elif isinstance(valor, dict):  
                for subvalor in valor.values():
                    if subvalor:
                        campos_con_datos += 1
                        break  
            elif isinstance(valor, str) and valor.strip():  
                campos_con_datos += 1

            if campos_con_datos >= min_campos:
                return True

        return False  



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
        1. Devuelve solo el JSON. **No agregues texto antes o después del JSON.**
        2. No uses comillas triples, ni bloques de código (`'''`).
        """

        try:
                response = requests.post(
                    "http://127.0.0.1:11434/api/chat",
                    json={"model": "llama3:8b", "messages": [{"role": "user", "content": prompt}]},
                    stream= True
                )

                json_response = ""
                for chunk in response.iter_lines():  # 🔄 Lee la respuesta en partes
                    if chunk:
                        try:
                            chunk_data = json.loads(chunk)
                            json_response += chunk_data.get("message", {}).get("content", "")
                        except json.JSONDecodeError:
                            continue  # Si hay un error, sigue leyendo
                print("🔍 Respuesta completa de Ollama:", json_response)

                # Intentar parsear directamente la respuesta
                try:
                    parsed_json = json.loads(json_response)
                    return parsed_json
                except json.JSONDecodeError:
                    print("⚠️ Ollama devolvió una respuesta inválida. Reintentando...")

                

        except requests.exceptions.RequestException as e:
                print(f"❌ Error de conexión con Ollama: {str(e)}")
                return None
        except json.JSONDecodeError as e:
                print(f"❌ Error al convertir JSON: {str(e)}")
                return None

        



    

    def save_species_to_postgres(self, structured_data_list, source_url, url, batch_size=250):
        try:
            if not structured_data_list:
                logger.warning("⚠️ Lista de datos estructurados vacía, no se guardará en PostgreSQL.")
                return

            print(f"🔍 Intentando guardar {len(structured_data_list)} especies en PostgreSQL")

            scraper_source, created = ScraperURL.objects.get_or_create(
                url=url, defaults={"Sobrenombre": "Fuente desconocida"}
            )
            logger.info(f"🗂️ Fuente asignada: {scraper_source.id} ({scraper_source.url})")

            species_objects = []

            for structured_data in structured_data_list:
                try:
                    scientific_name = (structured_data.get("nombre_cientifico") or "").strip()
                    if not scientific_name:
                        logger.warning("⚠️ Se descartó una especie sin nombre científico.")
                        continue

                    species_obj = Species(
                        scientific_name=scientific_name,

                        common_names=", ".join(structured_data.get("nombres_comunes", []))
                        if isinstance(structured_data.get("nombres_comunes"), list)
                        else structured_data.get("nombres_comunes", "") or "",

                        synonyms=json.dumps(structured_data.get("sinonimos", []))
                        if isinstance(structured_data.get("sinonimos"), list)
                        else "[]",

                        invasiveness_description=structured_data.get("descripcion_invasividad") or "",

                        distribution=json.dumps(structured_data.get("distribucion", []))
                        if isinstance(structured_data.get("distribucion"), list)
                        else "[]",

                        impact=json.dumps(structured_data.get("impacto", {}))
                        if isinstance(structured_data.get("impacto"), dict)
                        else "{}",

                        habitat=structured_data.get("habitat") or "",
                        life_cycle=structured_data.get("ciclo_vida") or "",
                        reproduction=structured_data.get("reproduccion") or "",

                        hosts=json.dumps(structured_data.get("hospedantes", []))
                        if isinstance(structured_data.get("hospedantes"), list)
                        else "[]",

                        symptoms=json.dumps(structured_data.get("sintomas", []))
                        if isinstance(structured_data.get("sintomas"), list)
                        else "[]",

                        affected_organs=json.dumps(structured_data.get("organos_afectados", []))
                        if isinstance(structured_data.get("organos_afectados"), list)
                        else "[]",

                        environmental_conditions=json.dumps(structured_data.get("condiciones_ambientales", []))
                        if isinstance(structured_data.get("condiciones_ambientales"), list)
                        else "[]",

                        prevention_control=json.dumps(structured_data.get("prevencion_control", {}))
                        if isinstance(structured_data.get("prevencion_control"), dict)
                        else "{}",

                        uses=json.dumps(structured_data.get("usos", []))
                        if isinstance(structured_data.get("usos"), list)
                        else "[]",

                        source_url=source_url,
                        scraper_source=scraper_source,
                    )
                    species_objects.append(species_obj)

                except Exception as e:
                    logger.error(
                        f"❌ Error al procesar especie '{structured_data.get('nombre_cientifico', 'Desconocido')}'"
                        f" - Detalle: {str(e)}"
                    )

            if species_objects:
                with transaction.atomic():
                    Species.objects.bulk_create(species_objects, batch_size=batch_size)
                logger.info(f"✅ {len(species_objects)} especies guardadas en PostgreSQL en lotes de {batch_size}.")
            else:
                logger.warning("⚠️ No se guardaron especies, todas fueron descartadas.")

        except Exception as e:
            logger.error(f"❌ Error al guardar en PostgreSQL: {str(e)}")


class ScraperComparisonService:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["collection"]

    def get_comparison_for_url(self, url):

        documents = list(self.collection.find({"url": url}).sort("scraping_date", -1))

        if len(documents) < 2:
            logger.info(f"No hay suficientes versiones de la URL {url} para comparar.")
            return {"status": "no_comparison", "message": "Menos de dos registros encontrados."}

        doc1, doc2 = documents[:2]  
        object_id1 = str(doc1["_id"])
        object_id2 = str(doc2["_id"])

        existing_report = ReportComparison.objects.filter(scraper_source__url=url).first()

        if existing_report and existing_report.object_id1 == object_id1 and existing_report.object_id2 == object_id2:
            logger.info(f"La comparación entre {object_id1} y {object_id2} ya existe y no ha cambiado.")
            return {"status": "duplicate", "message": "La comparación ya fue realizada anteriormente."}

        return self.compare_and_save(url, doc1, doc2)


    def compare_and_save(self, url, doc1, doc2):
        object_id1 = str(doc1["_id"])
        object_id2 = str(doc2["_id"])
        content1 = doc1.get("contenido", "")
        content2 = doc2.get("contenido", "")

        if not content1 or not content2:
            logger.warning(f"Uno de los documentos ({object_id1}, {object_id2}) no tiene contenido.")
            return {"status": "missing_content", "message": "Uno de los registros no tiene contenido."}

        comparison_result = self.generate_comparison_with_ollama(content1, content2, url, object_id1, object_id2)

        if comparison_result and comparison_result.get("has_changes", False):  
            self.save_or_update_comparison_to_postgres(url, object_id1, object_id2, comparison_result)
            return {"status": "changed", "message": "Se detectaron cambios en la comparación."}

        return {"status": "no_changes", "message": "No se detectaron cambios en la comparación."}
    


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