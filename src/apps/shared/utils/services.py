from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.utils.scrapers import SCRAPER_FUNCTIONS, scraper_pdf
from src.apps.shared.models.scraperURL import Species, ReportComparison
import logging
import concurrent
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime
import requests
import json
import re
import inspect
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)


class WebScraperService:
    def get_expired_urls(self):
        print("🔍 Primera llamada a filter()")
        queryset = ScraperURL.objects.filter(is_active=True)

        print("🔍 Segunda llamada a filter()")
        queryset = queryset.filter(
            Q(fecha_scraper__lt=datetime.now()) | 
            Q(fecha_scraper__isnull=True) | 
            Q(estado_scrapeo="fallido")
        )

        print("🔍 Llamada a exclude()")
        queryset = queryset.exclude(estado_scrapeo="en_progreso")

        return queryset.values_list("url", flat=True)


    def scraper_one_url(self, url, sobrenombre):
        try:
            logger.info(f"Intentando obtener URL {url} desde la base de datos")
            scraper_url = ScraperURL.objects.get(url=url)
            mode_scrapeo = scraper_url.mode_scrapeo

            scraper_function = SCRAPER_FUNCTIONS.get(mode_scrapeo)
            if not scraper_function:
                error_msg = f"Modo de scrapeo {mode_scrapeo} no registrado en SCRAPER_FUNCTIONS"
                scraper_url.estado_scrapeo = "fallido"
                scraper_url.error_scrapeo = error_msg
                scraper_url.fecha_scraper = timezone.now()
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
                    error_msg = f"Respuesta no serializable en scraper_pdf. Tipo recibido: {type(response)}"
                    scraper_url.estado_scrapeo = "fallido"
                    scraper_url.error_scrapeo = error_msg
                    scraper_url.fecha_scraper = timezone.now()
                    scraper_url.save()
                    return {"error": error_msg}

                scraper_url.estado_scrapeo = "exitoso"
                scraper_url.error_scrapeo = ""
                scraper_url.fecha_scraper = timezone.now()
                scraper_url.save()
                return response

            logger.info(f"Ejecutando scraper para {url} con método {mode_scrapeo}")

            params = inspect.signature(scraper_function).parameters
            response = scraper_function(url, sobrenombre) if len(params) == 2 else scraper_function(url)

            if not response or "error" in response:
                scraper_url.estado_scrapeo = "fallido"
                scraper_url.error_scrapeo = response.get("error", "Scraping no devolvió datos válidos.")
            else:
                scraper_url.estado_scrapeo = "exitoso"
                scraper_url.error_scrapeo = ""

            scraper_url.fecha_scraper = timezone.now()
            scraper_url.save()
            return response

        except ScraperURL.DoesNotExist:
            error_msg = f"La URL {url} no se encuentra en la base de datos."
            logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Error al ejecutar scraper para {url}: {str(e)}"

            # ✅ Asegurar que `scraper_url` existe antes de modificarlo
            if 'scraper_url' in locals():
                scraper_url.estado_scrapeo = "fallido"
                scraper_url.error_scrapeo = error_msg
                scraper_url.fecha_scraper = timezone.now()
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
            futures = {
                executor.submit(self.process_document, doc): doc for doc in documents
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(
                        f"❌ Error procesando documento {futures[future]}: {e}"
                    )

    def process_document(self, doc):
        content = doc.get("contenido", "")
        source_url = doc.get("source_url", "")
        mongo_id = doc["_id"]  

        if not content:
            logger.warning(f"Documento {mongo_id} no tiene contenido.")
            return

        existing_doc = self.collection.find_one({"_id": mongo_id, "processed": True})
        if existing_doc:
            logger.info(f"📌 Documento {mongo_id} ya fue procesado. Se ignora.")
            return

        structured_data = self.text_to_json(content, source_url, doc.get("url", ""))
        
        if not isinstance(structured_data, dict):
            logger.warning(f"❌ JSON inválido para {mongo_id}, no es un diccionario")
            return

        if datos_son_validos(structured_data):
            self.save_species_to_postgres(structured_data, source_url, doc.get("url", ""), mongo_id)

            self.collection.update_one(
                {"_id": mongo_id},
                {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
            )
            logger.info(f"✅ Procesado y guardado en PostgreSQL: {mongo_id}")
        else:
            logger.warning(f"⚠️ Datos vacíos para {mongo_id}, no se guardan en PostgreSQL.")

    def text_to_json(self, content, source_url, url):
        prompt = f"""
        Organiza el siguiente contenido en formato JSON con la siguiente estructura:
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
         **No uses comillas triples , ni bloques de código (`'''`).**
        - **Asegúrate de que el JSON devuelto tenga llaves de apertura y cierre correctamente.**

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
        14 **Evita respuestas como "Aquí está el JSON" o "Formato JSON esperado". Solo envía el JSON puro.**
        """

        response = requests.post(
            "http://127.0.0.1:11434/api/chat",
            json={
                "model": "llama3:8b",
                "messages": [{"role": "user", "content": prompt}],
            },
            stream=True,
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
                print("✅ JSON correctamente extraído:", parsed_json)

                # Asegurar que devuelve un diccionario y no una cadena de texto
                if isinstance(parsed_json, dict):
                    return parsed_json
                else:
                    print("⚠️ Error: `parsed_json` no es un diccionario válido.")
                    return None
            except json.JSONDecodeError as e:
                print(f"❌ Error al convertir JSON después de limpiar: {str(e)}")
                print("📌 Respuesta completa recibida:", full_response)
                print("📌 JSON detectado:", json_text)
                return None
        else:
            print("⚠️ No se encontró un JSON válido en la respuesta de Ollama.")
            return None

    
    def save_species_to_postgres(self, structured_data, source_url, url, mongo_id, batch_size=250):
        try:
            # Convertir strings en listas JSON válidas
            def ensure_list(value):
                """Convierte strings JSON en listas reales y asegura que el valor sea una lista."""
                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)
                        if not isinstance(parsed_value, list):
                            return [parsed_value]
                        return parsed_value
                    except json.JSONDecodeError:
                        return [value]  # Si falla la conversión, guarda como lista con un solo valor
                return value if isinstance(value, list) else []

            def ensure_dict(value):
                """Convierte strings JSON en diccionarios reales y asegura que el valor sea un diccionario."""
                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)
                        if isinstance(parsed_value, dict):
                            return parsed_value
                    except json.JSONDecodeError:
                        return {}  # Si falla la conversión, devuelve un diccionario vacío
                return value if isinstance(value, dict) else {}

            with transaction.atomic():
                species_obj, created = Species.objects.update_or_create(
                    source_url=source_url,
                    defaults={
                        "scientific_name": structured_data.get("nombre_cientifico", "").strip(),
                        "common_names": json.dumps(ensure_list(structured_data.get("nombres_comunes", []))),
                        "synonyms": json.dumps(ensure_list(structured_data.get("sinonimos", []))),
                        "distribution": json.dumps(ensure_list(structured_data.get("distribucion", []))),
                        "impact": ensure_dict(structured_data.get("impacto", {})),  # Guardar como JSON
                        "habitat": structured_data.get("habitat", ""),
                        "life_cycle": structured_data.get("ciclo_vida", ""),
                        "reproduction": structured_data.get("reproduccion", ""),
                        "hosts": json.dumps(ensure_list(structured_data.get("hospedantes", []))),
                        "symptoms": json.dumps(ensure_list(structured_data.get("sintomas", []))),
                        "affected_organs": json.dumps(ensure_list(structured_data.get("organos_afectados", []))),
                        "environmental_conditions": json.dumps(ensure_list(structured_data.get("condiciones_ambientales", []))),
                        "prevention_control": ensure_dict(structured_data.get("prevencion_control", {})),  # Guardar como JSON
                        "uses": json.dumps(ensure_list(structured_data.get("usos", []))),
                        "scraper_source": ScraperURL.objects.get(url=url),
                    },
                )

                if created:
                    logger.info(f"✅ Nueva especie guardada en PostgreSQL: {species_obj.scientific_name}")
                else:
                    logger.info(f"🔄 Especie actualizada en PostgreSQL: {species_obj.scientific_name}")

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
            return {
                "status": "no_comparison",
                "message": "Menos de dos registros encontrados.",
            }

        doc1, doc2 = documents[:2]
        object_id1, object_id2 = str(doc1["_id"]), str(doc2["_id"])

        existing_report = ReportComparison.objects.filter(scraper_source__url=url).first()

        if existing_report and existing_report.object_id1 == object_id1 and existing_report.object_id2 == object_id2:
            logger.info(f"La comparación entre {object_id1} y {object_id2} ya existe.")
            return {"status": "duplicate", "message": "La comparación ya fue realizada anteriormente."}

        return self.compare_and_save(url, doc1, doc2)

    def compare_and_save(self, url, doc1, doc2):

        object_id1, object_id2 = str(doc1["_id"]), str(doc2["_id"])
        content1, content2 = doc1.get("contenido", ""), doc2.get("contenido", "")

        if not content1 or not content2:
            logger.warning(f"Uno de los documentos ({object_id1}, {object_id2}) no tiene contenido.")
            return {"status": "missing_content", "message": "Uno de los registros no tiene contenido."}

        comparison_result = self.generate_comparison(content1, content2)

        if comparison_result and comparison_result.get("has_changes", False):
            self.save_or_update_comparison_to_postgres(url, object_id1, object_id2, comparison_result)
            return {"status": "changed", "message": "Se detectaron cambios en la comparación."}

        return {"status": "no_changes", "message": "No se detectaron cambios en la comparación."}

    def generate_comparison(self, content1, content2):

        urls1 = self.extract_urls(content1)
        urls2 = self.extract_urls(content2)

        new_urls = list(set(urls2) - set(urls1))
        removed_urls = list(set(urls1) - set(urls2))

        has_changes = bool(new_urls or removed_urls)

        return {
            "info_agregada": new_urls,
            "info_eliminada": removed_urls,
            "estructura_cambio": has_changes
        }

    def extract_urls(self, content):
        """
        Extrae las URLs de un reporte de scraping.
        """
        scraped_urls = []
        lines = content.split("\n")
        scraping_section = False

        for line in lines:
            line = line.strip()
            if "Enlaces scrapeados:" in line:
                scraping_section = True
                continue
            elif "Enlaces no procesados:" in line:
                break

            if scraping_section and line:
                scraped_urls.append(line)

        return scraped_urls

    def save_or_update_comparison_to_postgres(self, url, object_id1, object_id2, comparison_result):

        scraper_source, _ = ScraperURL.objects.get_or_create(url=url)

        ReportComparison.objects.update_or_create(
            scraper_source=scraper_source,
            object_id1=object_id1,
            object_id2=object_id2,
            defaults={
                "info_agregada": json.dumps(comparison_result["info_agregada"]),
                "info_eliminada": json.dumps(comparison_result["info_eliminada"]),
                "estructura_cambio": comparison_result["estructura_cambio"]
            }
        )
        logger.info(f"Comparación guardada para la URL {url}.")


def datos_son_validos(datos, min_campos=2):
    print("🔍 Evaluando JSON:", datos)

    if not datos or not isinstance(datos, dict):
        print("❌ JSON inválido: No es un diccionario")
        return False

    if not datos.get("nombre_cientifico") or not datos["nombre_cientifico"].strip():
        print("❌ JSON inválido: Falta nombre_cientifico")
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

    print("⚠️ JSON descartado por falta de datos")
    return False