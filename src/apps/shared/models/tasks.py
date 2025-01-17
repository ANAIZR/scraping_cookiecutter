from celery import shared_task
import requests
from django.utils.timezone import now
from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.users.models import User  # Importar el modelo donde está el token
import logging

logger = logging.getLogger(__name__)

@shared_task

def scrape_url():

    try:
        user = User.objects.filter(is_active=True).first()  
        if not user:
            logger.error("No se encontró un usuario activo.")
            return {"status": "error", "message": "No se encontró un usuario activo."}

        access_token = user.access_token  
        if not access_token:
            logger.error("El usuario no tiene un access_token.")
            return {"status": "error", "message": "El usuario no tiene un access_token."}
    except Exception as e:
        logger.critical(f"Error al obtener el token desde la base de datos: {str(e)}")
        return {"status": "error", "message": f"Error al obtener el token: {str(e)}"}

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        urls = ScraperURL.objects.filter(is_active=True).exclude(fecha_scraper__gt=now())

        for scraper in urls:
            try:
                if scraper.is_time_expired():
                    data = {"url": scraper.url}
                    response = requests.post(
                        "https://apiwebscraper.sgcan.dev/api/v1/scraper-url/", headers=headers, json=data
                    )
                    response.raise_for_status()
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
