from celery import shared_task
import requests
from django.utils.timezone import now
from src.apps.shared.models.scraperURL import ScraperURL
import logging
from dotenv import load_dotenv
import os
# Cargar las variables de entorno del archivo .env
load_dotenv()
logger = logging.getLogger(__name__)

@shared_task
def scrape_url():
    """
    Tarea que revisa todas las URLs activas y realiza el scrapeo si ha expirado su tiempo.
    """
    access_token = os.getenv("ACCESS_TOKEN")  # Obtener el token guardado

    if not access_token:
        return {"status": "error", "message": "No se encontró el access_token."}

    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        # Filtrar solo las URLs activas cuyo tiempo ha expirado
        urls = ScraperURL.objects.filter(is_active=True).exclude(fecha_scraper__gt=now())

        for scraper in urls:
            try:
                if scraper.is_time_expired():
                    data = {"url": scraper.url}
                    response = requests.post(
                        "http://127.0.0.1:8000/api/v1/scraper-url/", headers=headers,json=data
                    )
                    response.raise_for_status()

                    # Actualizar la fecha de scrapeo
                    scraper.fecha_scraper = now()
                    scraper.save()

                    logger.info(f"Scrapeo realizado para la URL: {scraper.url}")
                else:
                    logger.info(f"No es necesario scrapear la URL: {scraper.url}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error al hacer el scrapeo para {scraper.url}: {str(e)}")
            except Exception as e:
                logger.error(f"Error general para {scraper.url}: {str(e)}")

        return {"status": "success", "message": "Proceso completado"}
    except Exception as e:
        logger.critical(f"Error crítico en la tarea de scrapeo: {str(e)}")
        return {"status": "error", "message": f"Error general: {str(e)}"}
