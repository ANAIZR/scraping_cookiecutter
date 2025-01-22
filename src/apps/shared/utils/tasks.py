from celery import shared_task
from datetime import datetime
from ..models.scraperURL import ScraperURL
from .scrapers import SCRAPER_FUNCTIONS


@shared_task(bind=True)
def scrape_url_task(self, url):

    try:
        scraper_url = ScraperURL.objects.get(url=url)
        mode_scrapeo = scraper_url.mode_scrapeo
        scraper_function = SCRAPER_FUNCTIONS.get(mode_scrapeo)

        if not scraper_function:
            return {
                "status": "error",
                "message": f"Modo de scrapeo no reconocido: {mode_scrapeo}",
            }

        kwargs = {"url": url, "sobrenombre": scraper_url.sobrenombre}
        response = scraper_function(**kwargs)

        scraper_url.fecha_scraper = datetime.now()
        scraper_url.save()

        return {
            "status": "success",
            "message": "Scraping completado con éxito.",
            "data": response,
        }

    except ScraperURL.DoesNotExist:
        return {
            "status": "error",
            "message": f"No se encontraron parámetros para la URL: {url}",
        }
    except Exception as e:
        return {"status": "error", "message": f"Error durante el scraping: {str(e)}"}
