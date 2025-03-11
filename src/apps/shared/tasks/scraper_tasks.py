from celery import shared_task, chain
from src.apps.shared.services.scraper_service import WebScraperService
from src.apps.shared.services.ollama import OllamaService
from src.apps.shared.services.ollama_cabi import OllamaCabiService
from src.apps.shared.models.urls import ScraperURL
import logging
from django.utils import timezone
from src.apps.shared.tasks.comparison_tasks import generate_comparison_report_task
from src.apps.shared.tasks.notifications_tasks import check_new_species_task
from datetime import datetime
from ..utils.scrapers.cabi_digital import scraper_cabi_digital
logger = logging.getLogger(__name__)

from celery import chain
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


@shared_task(bind=True)
def scraper_cabi_task(self, url, *args, **kwargs):

    logger.info(f"🔍 Iniciando `scraper_cabi_task` en Celery para la URL: {url}")

    try:
        scraper_url = ScraperURL.objects.get(url=url)
        sobrenombre = scraper_url.sobrenombre

        scraper_url.estado_scrapeo = "en_progreso"
        scraper_url.error_scrapeo = ""
        scraper_url.fecha_scraper = datetime.now()
        scraper_url.save()

        result = scraper_cabi_digital(url, sobrenombre)

        if "error" in result:
            logger.error(f"❌ Scraping local fallido para {url}: {result['error']}")
            scraper_url.estado_scrapeo = "fallido"
            scraper_url.error_scrapeo = result["error"]
            scraper_url.save()
            return {"status": "failed", "url": url, "error": result["error"]}

        logger.info(f"✅ Scraping exitoso para {url}, resultado: {result}")
        scraper_url.estado_scrapeo = "exitoso"
        scraper_url.error_scrapeo = ""
        scraper_url.save()

        tareas = [
            process_scraped_data_task.si(url).set(ignore_result=True),
            generate_comparison_report_task.s().set(ignore_result=True),
        ]

        urls_permitidas = {
            "https://www.ippc.int/en/countries/south-africa/pestreports/",
            "https://www.pestalerts.org/nappo/emerging-pest-alerts/",
        }
        if url in urls_permitidas:
            tareas.append(check_new_species_task.si(url).set(ignore_result=True))

        if scraper_url.estado_scrapeo == "exitoso":
            chain(*tareas).apply_async()
            logger.info(f"✅ Flujo post-scraping ejecutado en Celery para {url}.")

        return {"status": scraper_url.estado_scrapeo, "url": url, "data": result}

    except ScraperURL.DoesNotExist:
        logger.error(f"❌ No se encontró `ScraperURL` para {url}")
        return {"status": "failed", "url": url, "error": "ScraperURL no encontrado"}

    except Exception as e:
        logger.error(f"❌ Error en `scraper_cabi_task`: {str(e)}")
        return {"status": "failed", "url": url, "error": str(e)}
@shared_task(bind=True)
def scraper_url_task(self, url, *args, **kwargs):
    if ScraperURL.objects.filter(url=url, estado_scrapeo="en_progreso").exists():
        logger.info(f"Task {self.request.id}: La URL {url} ya está en progreso.")
        return {"status": "skipped", "url": url, "message": "Scraping ya en progreso"}
    scraper_service = WebScraperService()

    try:
        scraper_url = ScraperURL.objects.get(url=url)
        sobrenombre = scraper_url.sobrenombre

        scraper_url.estado_scrapeo = "en_progreso"
        scraper_url.error_scrapeo = ""
        scraper_url.fecha_scraper = timezone.now()
        scraper_url.save()

    except ScraperURL.DoesNotExist:
        logger.error(f"Task {self.request.id}: No se encontró ScraperURL para {url}")
        return {"status": "failed", "url": url, "error": "ScraperURL no encontrado"}

    except Exception as e:
        logger.error(f"Task {self.request.id}: Error al actualizar fecha de scraping para {url}: {str(e)}")
        return {"status": "failed", "url": url, "error": str(e)}
    
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

    urls_permitidas = {
        "https://www.ippc.int/en/countries/south-africa/pestreports/",
        "https://www.pestalerts.org/nappo/emerging-pest-alerts/",
    }

    tareas = [
        process_scraped_data_task.si(url).set(ignore_result=True),
        generate_comparison_report_task.s().set(ignore_result=True),
    ]

    if url in urls_permitidas:
        tareas.append(check_new_species_task.si(url).set(ignore_result=True))

    if scraper_url.estado_scrapeo == "exitoso":
        chain(*tareas).apply_async()
    else:
        logger.warning(f"No se ejecuta `chain()` porque el scraping falló para {url}.")

    return {
        "status": scraper_url.estado_scrapeo,
        "url": url,
        "data": result if result else "No data scraped"
    }


@shared_task(bind=True)
def scraper_expired_urls_task(self, *args, **kwargs):
    scraper_service = WebScraperService()
    urls = scraper_service.get_expired_urls()

    if not urls:
        logger.info("No hay URLs expiradas para scrapear.")
        return

    try:
        logger.info(f"Iniciando scraping en secuencia para {len(urls)} URLs...")

        task_chain = chain(*[scraper_url_task.si(url) for url in urls])
        task_chain.apply_async()

        logger.info("Tareas encoladas en secuencia.")
    except Exception as e:
        logger.error(f"Error al encolar scraper en secuencia: {str(e)}")
