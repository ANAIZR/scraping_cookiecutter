from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.utils.scrapers import SCRAPER_FUNCTIONS, scraper_pdf
import logging
from datetime import datetime
import inspect
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)
class WebScraperService:
    def get_expired_urls(self):
        queryset = ScraperURL.objects.filter(is_active=True)

        queryset = queryset.filter(
            Q(fecha_scraper__lt=timezone.now()) | 
            Q(fecha_scraper__isnull=True) | 
            Q(estado_scrapeo="fallido")
        )

        queryset = queryset.exclude(estado_scrapeo="en_progreso")

        return queryset.values_list("url", flat=True)


    def scraper_one_url(self, url, sobrenombre):
        try:
            logger.info(f"Intentando obtener URL {url} desde la base de datos")
            scraper_url = ScraperURL.objects.get(url=url)
            mode_scrapeo = scraper_url.mode_scrapeo

            scraper_function = SCRAPER_FUNCTIONS.get(mode_scrapeo)
            if not scraper_function:
                error_msg = f"Modo de scrapeo {mode_scrapeo} no registrado en SCRAPER_FUNCTIONS"
                scraper_url.estado_scrapeo = "fallido"
                scraper_url.error_scrapeo = error_msg
                scraper_url.fecha_scraper = timezone.now()
                scraper_url.save()
                logger.error(error_msg)
                return {"error": error_msg}

            if mode_scrapeo == 7:
                parameters = scraper_url.parameters or {}
                start_page = parameters.get("start_page", 1)
                end_page = parameters.get("end_page", None)
                logger.info(f"Procesando PDF: {url}, páginas {start_page} - {end_page}")

                response = scraper_pdf(url, scraper_url.sobrenombre, start_page, end_page)

                if not isinstance(response, dict):
                    error_msg = f"Respuesta no serializable en scraper_pdf. Tipo recibido: {type(response)}"
                    scraper_url.estado_scrapeo = "fallido"
                    scraper_url.error_scrapeo = error_msg
                    scraper_url.fecha_scraper = timezone.now()
                    scraper_url.save()
                    return {"error": error_msg}

                scraper_url.estado_scrapeo = "exitoso"
                scraper_url.error_scrapeo = ""
                scraper_url.fecha_scraper = timezone.now()
                scraper_url.save()
                return response

            logger.info(f"Ejecutando scraper para {url} con método {mode_scrapeo}")

            params = inspect.signature(scraper_function).parameters
            response = scraper_function(url, sobrenombre) if len(params) == 2 else scraper_function(url)

            if not response or "error" in response:
                scraper_url.estado_scrapeo = "fallido"
                scraper_url.error_scrapeo = response.get("error", "Scraping no devolvió datos válidos.")
            else:
                scraper_url.estado_scrapeo = "exitoso"
                scraper_url.error_scrapeo = ""

            scraper_url.fecha_scraper = timezone.now()
            scraper_url.save()
            return response

        except ScraperURL.DoesNotExist:
            error_msg = f"La URL {url} no se encuentra en la base de datos."
            logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Error al ejecutar scraper para {url}: {str(e)}"

            if 'scraper_url' in locals():
                scraper_url.estado_scrapeo = "fallido"
                scraper_url.error_scrapeo = error_msg
                scraper_url.fecha_scraper = timezone.now()
                scraper_url.save()

            logger.error(error_msg)
            return {"error": error_msg}
