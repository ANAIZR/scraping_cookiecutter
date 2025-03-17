from src.apps.shared.models.species import SpeciesNews,Species
import concurrent
from concurrent.futures import ThreadPoolExecutor
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime
import requests
import json
import re
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

class NewsScraperService:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["news_articles"] 

    def extract_and_save_species(self, url):
        documents = list(self.collection.find({"url": url, "processed": {"$ne": True}}))
        if not documents:
            logger.info(f"🚫 No hay documentos pendientes para {url}.")
            return
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.process_news_document, doc): doc for doc in documents}

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"❌ Error procesando documento {futures[future]}: {e}")

    def process_news_document(self, doc):

        content = doc.get("contenido", "")
        source_url = doc.get("source_url", "")
        mongo_id = doc["_id"]

        existing_doc = self.collection.find_one({"_id": mongo_id})
        if existing_doc and existing_doc.get("processed"):
            logger.info(f"🔄 Documento {mongo_id} ya ha sido procesado. Se omite.")
            return

        if not content:
            logger.warning(f"🚫 Documento {mongo_id} no tiene contenido.")
            return

        structured_data = self.text_to_json(content, source_url, doc.get("url", ""))

        if not isinstance(structured_data, dict):
            logger.warning(f"❌ JSON inválido para {mongo_id}, no es un diccionario")
            return

        if datos_son_validos(structured_data):
            self.save_news_to_postgres(structured_data, source_url, doc.get("url", ""), mongo_id)

            self.collection.update_one(
                {"_id": mongo_id},
                {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
            )
            logger.info(f"✅ Noticia procesada y guardada en PostgreSQL: {mongo_id}")
        else:
            logger.warning(f"⚠️ Datos vacíos para {mongo_id}, no se guardan en PostgreSQL.")

    def text_to_json(self, content, source_url, url):
        """
        Extrae información estructurada de la noticia en formato JSON.
        """
        prompt = f"""
        Extrae información clave sobre una noticia científica en **formato JSON**.
        Contenido: {content}
        **Si un campo no tiene información, usa `""`.**
        **Estructura esperada:** 

        {{
          "nombre_cientifico": "",
          "distribucion": "",
          "resumen": "",
          "fecha_publicacion": "",
          "url": "{source_url}",
          "fuente": "{url}"
        }}

        **Contenido de la noticia:**
        {content}

        **Instrucciones:**
        - Devuelve solo el JSON, sin texto adicional.
        - Extrae la fecha de publicacion de esa url. La fecha debe estar en formato `YYYY-MM-DD`.
        - La distribución debe ser un string con países o regiones separados por comas.
        - El resumen debe ser un texto breve con la información principal.
        """

        response = requests.post(
            "http://100.122.137.82:11434/api/chat",
            json={"model": "llama3:70b", "messages": [{"role": "user", "content": prompt}]},
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

        match = re.search(r"\{.*\}", full_response, re.DOTALL)
        if match:
            json_text = match.group(0)
            try:
                parsed_json = json.loads(json_text)
                print("✅ JSON correctamente extraído:", parsed_json)
                return parsed_json if isinstance(parsed_json, dict) else None
            except json.JSONDecodeError as e:
                print(f"❌ Error al convertir JSON: {e}")
                return {}
        

    def save_news_to_postgres(self, structured_data, source_url, url, mongo_id):

        with transaction.atomic():
            news_obj, created = SpeciesNews.objects.update_or_create(
                source_url=source_url,
                defaults={
                    "scientific_name": structured_data.get("nombre_cientifico", "").strip(),  
                    "distribution": structured_data.get("distribucion", ""),
                    "summary": structured_data.get("resumen", ""),
                    "publication_date": structured_data.get("fecha_publicacion", ""),
                    "source_url": source_url,
                },
            )

            if created:
                logger.info(f"✅ Nueva noticia guardada en PostgreSQL: {news_obj.source_url}")
            else:
                logger.info(f"🔄 Noticia actualizada en PostgreSQL: {news_obj.source_url}")



def datos_son_validos(datos, min_campos=2):
    """
    Verifica si el JSON tiene suficientes datos válidos para ser guardado.
    """
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
