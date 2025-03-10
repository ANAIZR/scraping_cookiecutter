from apps.shared.models.urls import ScraperURL
from apps.shared.models.species import Species
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

class OllamaService:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["fs.files"]

    def extract_and_save_species(self, url):
        documents = list(self.collection.find({"url": url, "processed": {"$ne": True}}))

        if not documents:
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
        Organiza el siguiente contenido en **formato JSON**, pero 
        **cada campo que contenga múltiples valores debe estar separado por comas dentro de un string, en lugar de usar un array JSON**.
        **Cada campo con múltiples valores debe ser un string separado por comas**, en lugar de un array JSON.
        **Las secciones `prevencion_control` e `impacto` deben mantenerse como objetos anidados con sus claves correspondientes.**
        **Si un campo no tiene información, usa `""`.**
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
            def ensure_list(value):
                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)
                        if not isinstance(parsed_value, list):
                            return [parsed_value]
                        return parsed_value
                    except json.JSONDecodeError:
                        return [value]  
                return value if isinstance(value, list) else []

            def ensure_dict(value):
                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)
                        if isinstance(parsed_value, dict):
                            return parsed_value
                    except json.JSONDecodeError:
                        return {}  
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