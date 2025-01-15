""" from celery import shared_task
import requests
from models import ScraperURL

@shared_task
def scrape_url(scraper_id):
    
    try:
        scraper = ScraperURL.objects.get(id=scraper_id)
        if scraper.is_time_expired():
            data = {"url": scraper.url}
            response = requests.post(
                "http://127.0.0.1:8000/api/v1/scraper-url/", json=data
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "not_expired"}
    except ScraperURL.DoesNotExist:
        return {"status": "error", "message": "Scraper no encontrado."}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}
 """