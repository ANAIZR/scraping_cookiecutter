from src.apps.shared.models.urls import ScraperURL
from src.apps.shared.models.species import CabiSpecies
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime
import requests
import os
import json
import re
import logging
from bson.objectid import ObjectId
from django.db import transaction
from dotenv import load_dotenv
load_dotenv()
OLLAMA_URI =  os.getenv("OLLAMA_URI")
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
                logger.error(f"❌ Error procesando documento CABI: {e}", exc_info=True)

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

            # 🔍 Obtener datos ya extraídos desde MongoDB
            structured_data = {
                "scientific_name": document.get("nombre_cientifico", ""),
                "hosts": document.get("hospedantes", ""),
                "distribution": document.get("distribucion", ""),
                "common_names": document.get("common_names", ""),
                "synonyms": document.get("synonyms", ""),
                "habitat": document.get("habitat", ""),
                "reproduction": document.get("reproduction", ""),
                "affected_organs": document.get("affected_organs", ""),
                "source_url": source_url,
            }

            # Solo estos campos se resumirán con IA (Ollama)
            fields_to_summarize = {
                "environmental_conditions": document.get("ambiental_section", ""),
                "symptoms": document.get("symptoms", ""),
                "impact": document.get("impact", ""),
                "invasiveness_description": document.get("invasiveness_description", ""),
            }

            summarized_data = self.analyze_content_with_ollama(fields_to_summarize, source_url)

            if summarized_data:
                structured_data.update(summarized_data)

            if self.datos_son_validos(structured_data):
                self.save_species_to_postgres(structured_data, mongo_id)
                
                self.collection.update_one(
                    {"_id": ObjectId(mongo_id)},
                    {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
                )
                logger.info(f"✅ Procesado y guardado en PostgreSQL: {mongo_id}")
            else:
                logger.warning(f"⚠️ Datos vacíos para {mongo_id}, no se guardan en PostgreSQL.")

        except Exception as e:
            logger.error(f"🚨 Error procesando documento CABI {mongo_id}: {e}", exc_info=True)

    def analyze_content_with_ollama(self, fields_to_summarize, source_url):
        
        fields_to_summarize = {k: v.strip() for k, v in fields_to_summarize.items() if v and v.strip()}
        
        if not fields_to_summarize:
            logger.info("📭 No hay contenido para resumir con IA.")
            return {}

        prompt = f"""
        Extrae la información relevante sobre los siguientes campos en JSON.  
        **No inventes datos** y usa el texto proporcionado para generar un resumen claro.  
        Si un campo está vacío, devuelve `""`.  

        **Texto a analizar:**  
        {json.dumps(fields_to_summarize, indent=2, ensure_ascii=False)}

        **Formato de salida esperado:**  
        {{"environmental_conditions": "", "symptoms": "", "impact": "", "invasiveness_description": ""}}

        ⚠️ **Instrucciones Importantes:**  
        - No uses comillas triples ni bloques de código.  
        - Devuelve solo el JSON sin texto adicional.  
        - Extrae detalles clave de cada campo sin repetir información innecesaria.  
        """

        try:
            response = requests.post(
                OLLAMA_URI,
                json={"model": "llama3:8b", "messages": [{"role": "user", "content": prompt}]},
                stream=True,
            )

            if response.status_code != 200:
                logger.error(f"❌ Error en la petición a Ollama: {response.status_code} - {response.text}")
                return {}

            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        json_line = json.loads(line.decode("utf-8"))
                        message_content = json_line.get("message", {}).get("content", "")
                        full_response += message_content
                    except json.JSONDecodeError:
                        logger.error(f"❌ Error al decodificar JSON parcial de Ollama: {line}")

            match = re.search(r"\{.*\}", full_response, re.DOTALL)
            if match:
                json_text = match.group(0)
                summarized_data = json.loads(json_text)

                # 🔍 Validar que el resumen contiene información real
                for key, value in summarized_data.items():
                    if not value.strip() or "No encontrado" in value or len(value.strip()) < 5:
                        logger.warning(f"⚠️ Resumen insuficiente para '{key}', no se usará: {value}")
                        summarized_data[key] = ""  # Evitar guardar basura

                return summarized_data

            else:
                logger.warning(f"⚠️ No se encontró un JSON válido en la respuesta de Ollama: {full_response[:500]}")
                return {}

        except requests.RequestException as e:
            logger.error(f"❌ Error en la petición a Ollama: {str(e)}")
            return {}


    def save_species_to_postgres(self, structured_data, mongo_id):
        """Guarda o actualiza la información en PostgreSQL."""
        try:
            field_mapping = {
                "scientific_name": "scientific_name",
                "common_names": "common_names",
                "synonyms": "synonyms",
                "invasiveness_description": "invasiveness_description",
                "distribution": "distribution",
                "impact": "impact",
                "habitat": "habitat",
                "reproduction": "reproduction",
                "hosts": "hosts",
                "symptoms": "symptoms",
                "affected_organs": "affected_organs",
                "environmental_conditions": "environmental_conditions",
                "source_url": "source_url",
            }

            def list_to_string(value):
                if isinstance(value, list):
                    return ", ".join(str(v).strip() for v in value if v)
                return str(value).strip() if value else ""

            structured_data = {field_mapping[k]: list_to_string(v) for k, v in structured_data.items() if k in field_mapping}

            if not structured_data.get("scientific_name"):
                logger.warning(f"⚠️ Documento {mongo_id} descartado: scientific_name vacío. No se guarda en PostgreSQL.")
                return

            with transaction.atomic():
                species_obj, created = CabiSpecies.objects.update_or_create(
                    source_url=structured_data.get("source_url"),
                    defaults=structured_data,
                )

                if created:
                    logger.info(f"✅ Nueva especie guardada en PostgreSQL: {species_obj.scientific_name}")
                else:
                    logger.info(f"🔄 Especie actualizada en PostgreSQL: {species_obj.scientific_name}")

        except Exception as e:
            logger.error(f"❌ Error al guardar en PostgreSQL: {str(e)}", exc_info=True)

    def datos_son_validos(self, datos, min_campos=2):
        valores_invalidos = {"", None, "No encontrado", "N/A", "-", "Desconocido"}
        
        if datos.get("scientific_name") in valores_invalidos:
            logger.warning(f"🚫 Documento descartado: 'scientific_name' inválido ({datos.get('scientific_name')}).")
            return False

        campos_validos = [
            datos.get("common_names"),
            datos.get("distribution"),
            datos.get("symptoms"),
            datos.get("impact"),
            datos.get("habitat"),
        ]
        
        campos_utiles = [campo for campo in campos_validos if campo and campo.strip() not in valores_invalidos]
        
        return len(campos_utiles) >= min_campos
