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

            # 🔍 Obtén los datos de MongoDB primero
            existing_data = {
                "nombre_cientifico": document.get("nombre_cientifico", ""),
                "hospedantes": document.get("hospedantes", ""),
                "distribucion": document.get("distribucion", "")
            }

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
            logger.error(f"🚨 Error procesando documento CABI {mongo_id}: {e}", exc_info=True)


    def get_existing_species_data(self, object_id):
        document = self.collection.find_one({"_id": ObjectId(object_id)})
        if document:
            extracted_data = {
                "nombre_cientifico": document.get("nombre_cientifico", ""),
                "hospedantes": document.get("hospedantes", ""),
                "distribucion": document.get("distribucion", "")
            }
            logger.info(f"📦 Datos extraídos de MongoDB: {json.dumps(extracted_data, indent=2, ensure_ascii=False)}")
            return extracted_data
        logger.warning(f"🚫 Documento con ID {object_id} no encontrado en MongoDB.")
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
        
        **Mantén los siguientes campos sin cambios:**
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
            # 🔍 Validar si el JSON tiene claves incorrectas antes de guardar
            allowed_fields = {
                "scientific_name", "common_names", "synonyms", "distribution",
                "impact", "habitat", "life_cycle", "reproduction", "hosts",
                "symptoms", "affected_organs", "environmental_conditions",
                "prevention_control", "uses", "source_url", "created_at", "scraper_source"
            }

            structured_data = {k: v for k, v in structured_data.items() if k in allowed_fields}

            # ❌ Si el nombre científico es "No encontrado", no guardar
            scientific_name = structured_data.get("scientific_name", "").strip().lower()
            if scientific_name == "no encontrado":
                logger.warning(f"⚠️ Documento {mongo_id} descartado: scientific_name es 'No encontrado'. No se guarda en PostgreSQL.")
                return  # 🚨 Salimos de la función sin guardar

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
            logger.error(f"❌ Error al guardar en PostgreSQL: {str(e)}", exc_info=True)

    # 🔹 Agrega traceback para mejor debugging




    def datos_son_validos(self, datos, min_campos=2):
        campos_con_datos = sum(bool(datos.get(campo)) for campo in datos)
        return campos_con_datos >= min_campos
    

