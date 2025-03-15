from src.apps.shared.models.urls import ScraperURL
from src.apps.shared.models.species import CabiSpecies
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime
import requests
import json
import re
import logging
from bson.objectid import ObjectId
from django.db import transaction

logger = logging.getLogger(__name__)

class OllamaCabiService:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["cabi_scraper"]
        self.cabi_url = "https://www.cabidigitallibrary.org/product/qc"

    def extract_and_save_species(self, url):
        """Extrae y procesa documentos no procesados de una URL específica."""
        documents = list(self.collection.find({"url": url, "processed": {"$ne": True}}))

        if not documents:
            logger.info(f"🚫 No hay documentos pendientes de procesar para CABI ({url}).")
            return

        for document in documents:
            try:
                self.process_document(document["_id"])
            except Exception as e:
                logger.error(f"❌ Error procesando documento CABI: {e}")

    def process_document(self, mongo_id):
        try:
            document = self.collection.find_one({"_id": ObjectId(mongo_id)})

            if not document:
                logger.warning(f"🚫 No se encontró el documento con ID {mongo_id} en MongoDB.")
                return

            content = document.get("contenido", "")
            source_url = document.get("source_url", "")

            if not content:
                logger.warning(f"🚫 Documento {mongo_id} no tiene contenido.")
                return

            existing_data = self.get_existing_species_data(mongo_id)

            structured_data = self.analyze_content_with_ollama(content, source_url, existing_data)

            if not isinstance(structured_data, dict):
                logger.warning(f"❌ JSON inválido para {mongo_id}, no es un diccionario")
                return

            if self.datos_son_validos(structured_data):
                self.save_species_to_postgres(structured_data, source_url, mongo_id)

                self.collection.update_one(
                    {"_id": ObjectId(mongo_id)},
                    {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
                )
                logger.info(f"✅ Procesado y guardado en PostgreSQL: {mongo_id}")
            else:
                logger.warning(f"⚠️ Datos vacíos para {mongo_id}, no se guardan en PostgreSQL.")

        except Exception as e:
            logger.error(f"🚨 Error procesando documento CABI {mongo_id}: {e}")

    def get_existing_species_data(self, object_id):
        """Obtiene nombre científico, hospedantes y distribución directamente de MongoDB."""
        document = self.collection.find_one({"_id": ObjectId(object_id)})
        if document:
            return {
                "nombre_cientifico": document.get("nombre_cientifico", ""),
                "hospedantes": document.get("hospedantes", ""),
                "distribucion": document.get("distribucion", "")
            }
        return {}

    def analyze_content_with_ollama(self, content, source_url, existing_data):

        nombre_cientifico = existing_data.get("nombre_cientifico", "")
        hospedantes = existing_data.get("hospedantes", "")
        distribucion = existing_data.get("distribucion", "")

        prompt = f"""
        Organiza el siguiente contenido en **formato JSON**, pero 
        **cada campo que contenga múltiples valores debe estar separado por comas dentro de un string, en lugar de usar un array JSON**.
        **Las secciones `prevencion_control` e `impacto` deben mantenerse como objetos anidados con sus claves correspondientes.**
        **Si un campo no tiene información, usa `""`.**
        
        **Los siguientes campos ya han sido extraídos y deben mantenerse sin cambios:**
        - `nombre_cientifico`: {nombre_cientifico}
        - `hospedantes`: {hospedantes}
        - `distribucion`: {distribucion}

        **Contenido restante a analizar por IA:**
        {content}
        
        **Estructura esperada en JSON:** 

        {{
          "nombre_cientifico": "{nombre_cientifico}",
          "nombres_comunes": "",
          "sinonimos": "",
          "descripcion_invasividad": "",
          "distribucion": "{distribucion}",
          "impacto": {{"Económico": "", "Ambiental": "", "Social": ""}},
          "habitat": "",
          "ciclo_vida": "",
          "reproduccion": "",
          "hospedantes": "{hospedantes}",
          "sintomas": "",
          "organos_afectados": "",
          "condiciones_ambientales": "",
          "prevencion_control": {{"Prevención": "", "Control": ""}},
          "usos": "",
          "url": "{source_url}",
          "hora": "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
          "fuente": "{self.cabi_url}"
        }}

        **Instrucciones:**
        Devuelve solo el JSON. **No agregues texto antes o después del JSON.**
         **No uses comillas triples , ni bloques de código (`'''`).**
        - **Asegúrate de que el JSON devuelto tenga llaves de apertura y cierre correctamente.**

        1. Extrae los nombres comunes de la especie.
        2. Lista los sinónimos científicos si están disponibles.
        3. Extrae información sobre impacto económico, ambiental y social.
        4. Describe el hábitat donde se encuentra.
        5. Explica el ciclo de vida y los métodos de reproducción.
        6. Describe los síntomas y los órganos afectados en los hospedantes.
        7. Extrae las condiciones ambientales clave como temperatura, humedad y precipitación.
        8. Extrae información sobre métodos de prevención y control.
        9. Lista los usos conocidos de la especie.
            Devuelve solo el JSON con los datos extraídos, sin texto adicional.
        10 **Evita respuestas como "Aquí está el JSON" o "Formato JSON esperado". Solo envía el JSON puro.**
        """
        try:
            response = requests.post(
                "http://100.122.137.82:11434/api/chat"
    ,
                json={"model": "llama3:70b", "messages": [{"role": "user", "content": prompt}]},
                stream=True,
            )

            if response.status_code != 200:
                logger.error(f"❌ Error en la petición a Ollama: {response.status_code} - {response.text}")
                return None

            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        json_line = json.loads(line.decode("utf-8"))
                        message_content = json_line.get("message", {}).get("content", "")
                        full_response += message_content  # 🟢 Ensamblamos las partes de la respuesta
                    except json.JSONDecodeError:
                        logger.error(f"❌ Error al decodificar JSON parcial de Ollama: {line}")

            logger.info(f"📥 Respuesta completa de Ollama (500 caracteres): {full_response[:500]}")

            match = re.search(r"\{.*\}", full_response, re.DOTALL)
            if match:
                json_text = match.group(0)
                logger.info(f"✅ JSON extraído de la respuesta de Ollama: {json_text}")  # Ver JSON antes de convertir

                try:
                    structured_data = json.loads(json_text)
                    if isinstance(structured_data, dict):
                        return structured_data
                    else:
                        logger.warning(f"❌ JSON inválido para {source_url}, no es un diccionario")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Error al convertir JSON de Ollama: {str(e)}")
                    return None
            else:
                logger.warning(f"⚠️ No se encontró un JSON válido en la respuesta de Ollama: {full_response[:500]}")
                return None
        except requests.RequestException as e:
            logger.error(f"❌ Error en la petición a Ollama: {str(e)}")
            return None
        
    


    def save_species_to_postgres(self, structured_data, source_url, mongo_id):
        try:
            # Mapeo de nombres de campos del JSON a los nombres en el modelo Django
            mapeo_campos = {
                "nombre_cientifico": "scientific_name",
                "nombres_comunes": "common_names",
                "sinonimos": "synonyms",
                "descripcion_invasividad": "invasiveness_description",
                "distribucion": "distribution",
                "impacto": "impact",
                "habitat": "habitat",
                "ciclo_vida": "life_cycle",
                "reproduccion": "reproduction",
                "hospedantes": "hosts",
                "sintomas": "symptoms",
                "organos_afectados": "affected_organs",
                "condiciones_ambientales": "environmental_conditions",
                "prevencion_control": "prevention_control",
                "usos": "uses",
                "url": "source_url",
                "hora": "created_at",
                "fuente": "scraper_source"
            }

            # Renombrar los campos del JSON antes de guardarlos en PostgreSQL
            structured_data = {mapeo_campos.get(k, k): v for k, v in structured_data.items()}

            # Convertir listas en cadenas antes de guardar
            def safe_get_string(value):
                if isinstance(value, list):
                    return ", ".join(str(v).strip() for v in value if v)
                return str(value).strip() if value else ""

            for key in structured_data:
                structured_data[key] = safe_get_string(structured_data[key])

            nombre_cientifico = structured_data.get("scientific_name", "").lower()

            if nombre_cientifico == "no encontrado":
                logger.warning(f"⚠️ Documento {mongo_id} descartado: nombre_cientifico es 'No encontrado'.")
                return

            with transaction.atomic():
                species_obj, created = CabiSpecies.objects.update_or_create(
                    source_url=source_url,
                    defaults=structured_data,
                )

                if created:
                    logger.info(f"✅ Nueva especie guardada en PostgreSQL: {species_obj.scientific_name}")
                else:
                    logger.info(f"🔄 Especie actualizada en PostgreSQL: {species_obj.scientific_name}")

        except Exception as e:
            logger.error(f"❌ Error al guardar en PostgreSQL: {str(e)}")



    def datos_son_validos(self, datos, min_campos=2):
        campos_con_datos = sum(bool(datos.get(campo)) for campo in datos)
        return campos_con_datos >= min_campos
    

