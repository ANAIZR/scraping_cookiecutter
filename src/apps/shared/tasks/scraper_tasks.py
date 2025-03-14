from celery import shared_task, chain
from src.apps.shared.services.scraper_service import WebScraperService
from apps.shared.services.urls_ollama_service import OllamaService
from apps.shared.services.cabi_ollama_service import OllamaCabiService
from src.apps.shared.models.urls import ScraperURL
import logging
from django.utils import timezone
from src.apps.shared.tasks.comparison_tasks import generate_comparison_report_task
from src.apps.shared.tasks.notifications_tasks import check_new_species_task
from celery import chain
from django.db import transaction
from django.utils import timezone
import logging
logger = logging.getLogger(__name__)

CABI_URL = "https://www.cabidigitallibrary.org/product/qc"

@shared_task(bind=True)
def process_scraped_data_task(self, url, *args, **kwargs):
    if not url:
        logger.error("No se recibió una URL válida en process_scraped_data_task")
        return None

    if url == CABI_URL:
        logger.info(f"🔍 Usando OllamaCabiService para {url}")
        scraper = OllamaCabiService()
    else:
        logger.info(f"🔍 Usando OllamaService para {url}")
        scraper = OllamaService()

    scraper.extract_and_save_species(url) 

    return url


@shared_task(bind=True, max_retries=2)
def scraper_url_task(self, url, *args, **kwargs):
    """
    Tarea Celery para scrapear una URL. Se asegura de que la URL no se procese múltiples veces en paralelo.
    """

    try:
        with transaction.atomic():
            try:
                scraper_url = ScraperURL.objects.select_for_update(nowait=True).get(url=url)

                if scraper_url.estado_scrapeo == "en_progreso":
                    logger.info(f"Task {self.request.id}: La URL {url} ya está en progreso.")
                    return {"status": "skipped", "url": url, "message": "Scraping ya en progreso"}

                scraper_url.estado_scrapeo = "en_progreso"
                scraper_url.error_scrapeo = ""
                scraper_url.fecha_scraper = timezone.now()
                scraper_url.save()

            except ScraperURL.DoesNotExist:
                logger.error(f"Task {self.request.id}: No se encontró ScraperURL para {url}")
                return {"status": "failed", "url": url, "error": "ScraperURL no encontrado"}

            except Exception as e:
                logger.error(f"Task {self.request.id}: Error al bloquear la URL {url}: {str(e)}")
                return {"status": "failed", "url": url, "error": "No se pudo bloquear la URL"}

        scraper_service = WebScraperService()
        sobrenombre = scraper_url.sobrenombre
        result = scraper_service.scraper_one_url(url, sobrenombre)

        if "error" in result:
            logger.error(f"Task {self.request.id}: Scraping fallido para {url}: {result['error']}")
            scraper_url.estado_scrapeo = "fallido"
            scraper_url.error_scrapeo = result["error"]
            scraper_url.save()
            return {"status": "failed", "url": url, "error": result["error"]}

        logger.info(f"Task {self.request.id}: Scraping exitoso para {url}, resultado: {result}")
        scraper_url.estado_scrapeo = "exitoso"
        scraper_url.error_scrapeo = ""
        scraper_url.save()

        tareas = [
            process_scraped_data_task.si(url).set(ignore_result=True),
            generate_comparison_report_task.s().set(ignore_result=True),
        ]

        chain(*tareas).apply_async()
        logger.info(f"Task {self.request.id}: Se ha encadenado el procesamiento para {url}")

        return {
            "status": scraper_url.estado_scrapeo,
            "url": url,
            "data": result if result else "No data scraped"
        }

    except Exception as e:
        logger.error(f"Task {self.request.id}: Error inesperado en el scraping de {url}: {str(e)}")
        raise self.retry(exc=e, countdown=30)
    
@shared_task(bind=True, max_retries=3)
def scraper_expired_urls_task(self, *args, **kwargs):
    try:
        scraper_service = WebScraperService()
        urls = scraper_service.get_expired_urls() or []

        if not urls:
            logger.info("No hay URLs expiradas para scrapear.")
            return

        logger.info(f"Iniciando scraping en secuencia para {len(urls)} URLs...")

        task_chain = chain(*[scraper_url_task.si(url) for url in urls])
        task_chain.apply_async()

        logger.info("Tareas encoladas en secuencia correctamente.")
    except Exception as e:
        logger.error(f"Error al encolar scraper en secuencia: {str(e)}")
        raise self.retry(exc=e, countdown=60)  