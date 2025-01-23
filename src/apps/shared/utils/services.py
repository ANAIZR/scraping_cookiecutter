from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.utils.scrapers import SCRAPER_FUNCTIONS

import logging

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
            if mode_scrapeo == 7:  # scraper_pdf
                kwargs["start_page"] = scraper_url.start_page
                kwargs["end_page"] = scraper_url.end_page

            response = scraper_function(**kwargs)

            if isinstance(response, dict):  # Verifica que sea un diccionario
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


