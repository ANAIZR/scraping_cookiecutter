from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.utils.scrapers import SCRAPER_FUNCTIONS
from src.apps.shared.models.scraperURL import Species
import logging
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime
from ollama import chat
import json

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
        self.collection = self.db["files.fs"]

    def extract_and_save_species(self):

        documents = self.collection.find({"processed": {"$ne": True}})

        for doc in documents:
            content = doc.get("content", "")
            source_url = doc.get("source_url", "")
            scraper_source = doc.get("url", "")

            if not content:
                logger.warning(f"Documento {doc['_id']} no tiene contenido.")
                continue

            structured_data = self.text_to_json(content, source_url, scraper_source)

            if structured_data:
                self.save_species_to_postgres(
                    structured_data, source_url, scraper_source
                )

                self.collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
                )
                logger.info(f"Procesado y guardado en PostgreSQL: {doc['_id']}")

    def text_to_json(self, content, source_url, scraper_source):

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
          "fuente": "{scraper_source}",
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
            Devuelve solo el JSON con los datos extraídos, sin texto adicional.
        """

        response = chat(model="llama3", messages=[{"role": "user", "content": prompt}])

        try:
            return json.loads(response["message"]["content"])
        except json.JSONDecodeError:
            logger.error("Error al convertir la respuesta de `ollama` a JSON.")
            return None

    def save_species_to_postgres(self, structured_data, source_url, scraper_source):

        try:
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
