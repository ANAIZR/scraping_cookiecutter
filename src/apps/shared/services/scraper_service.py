from src.apps.shared.models.urls import ScraperURL
from src.apps.shared.utils.scrapers import SCRAPER_FUNCTIONS, scraper_pdf
import logging
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from inspect import signature

logger = logging.getLogger(__name__)

class WebScraperService:
    @staticmethod
    def update_scraper_status(scraper_url, estado, error_msg=""):

        if scraper_url:
            scraper_url.estado_scrapeo = estado
            scraper_url.error_scrapeo = error_msg
            scraper_url.fecha_scraper = timezone.now()
            scraper_url.save()

    @staticmethod
    def handle_error(scraper_url, error_msg):

        if scraper_url:
            WebScraperService.update_scraper_status(scraper_url, "fallido", error_msg)
        logger.error(error_msg)
        return {"error": error_msg}

    @staticmethod
    def execute_scraper_function(scraper_function, url, sobrenombre):

        sig = signature(scraper_function)
        num_params = len(sig.parameters)

        if num_params == 1:
            return scraper_function(url)
        elif num_params == 2:
            return scraper_function(url, sobrenombre)
        else:
            raise ValueError(f"Scraper function {scraper_function.__name__} tiene un número inesperado de parámetros.")

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

        scraper_url = None  

        try:
            logger.info(f"Intentando obtener URL {url} desde la base de datos")
            scraper_url = ScraperURL.objects.select_related().get(url=url)
            mode_scrapeo = scraper_url.mode_scrapeo

            scraper_function = SCRAPER_FUNCTIONS.get(mode_scrapeo)
            if not scraper_function:
                return WebScraperService.handle_error(scraper_url, f"Modo de scrapeo {mode_scrapeo} no registrado en SCRAPER_FUNCTIONS")

            if mode_scrapeo == 7:
                parameters = scraper_url.parameters or {}
                start_page = parameters.get("start_page", 1)
                end_page = parameters.get("end_page", None)
                logger.info(f"Procesando PDF: {url}, páginas {start_page} - {end_page}")

                response = scraper_pdf(url, scraper_url.sobrenombre, start_page, end_page)

                if not isinstance(response, dict):
                    return WebScraperService.handle_error(scraper_url, f"Respuesta no serializable en scraper_pdf. Tipo recibido: {type(response)}")

                WebScraperService.update_scraper_status(scraper_url, "exitoso")
                return response

            logger.info(f"Ejecutando scraper para {url} con método {mode_scrapeo}")
            response = WebScraperService.execute_scraper_function(scraper_function, url, sobrenombre)

            if not response or "error" in response:
                return WebScraperService.handle_error(scraper_url, response.get("error", "Scraping no devolvió datos válidos."))

            WebScraperService.update_scraper_status(scraper_url, "exitoso")
            return response

        except ScraperURL.DoesNotExist:
            return WebScraperService.handle_error(None, f"La URL {url} no se encuentra en la base de datos.")

        except Exception as e:
            return WebScraperService.handle_error(scraper_url, f"Error al ejecutar scraper para {url}: {str(e)}") if scraper_url else {"error": f"Error crítico: {str(e)}"}
