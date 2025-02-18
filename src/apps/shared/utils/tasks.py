from celery import shared_task
from src.apps.shared.utils.services import WebScraperService, ScraperService
from src.apps.shared.models.scraperURL import ScraperURL
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def scraper_expired_urls_task(self):
    scraper_service = WebScraperService()
    scraper_service.scraper_expired_urls()

@shared_task(bind=True)
def scraper_url_task(self, url):
    scraper_service = WebScraperService()
    result = scraper_service.scraper_one_url(url)

    try:
        scraper_url = ScraperURL.objects.get(url=url)
        scraper_url.fecha_scraper = datetime.now()
        scraper_url.save()
    except Exception as e:
        logger.error(f"Error al actualizar fecha de scraping para {url}: {str(e)}")
    if "error" in result:
        logger.error(f"Scraping fallido para {url}: {result['error']}")
    return result

@shared_task
def run_scraper_task():
    scraper = ScraperService()
    scraper.extract_and_save_species()