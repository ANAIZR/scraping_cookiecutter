from celery import shared_task
from .models import ScraperURL
import requests

@shared_task
def post_to_api_task(url_id):
    try:
        scraper_url = ScraperURL.objects.get(id=url_id)
        if scraper_url.is_time_expired():
            data = {"url": scraper_url.url}
            response = requests.post(
                "http://127.0.0.1:8000/api/v1/scraper-url/", json=data
            )
            response.raise_for_status()
            return response.json()
        return "El tiempo límite no ha expirado aún."
    except ScraperURL.DoesNotExist:
        return "ScraperURL no encontrado."
    except requests.exceptions.RequestException as e:
        return f"Error al hacer el POST a la API: {e}"
