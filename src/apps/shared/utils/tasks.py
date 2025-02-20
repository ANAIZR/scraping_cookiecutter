from celery import shared_task, chain
from src.apps.shared.utils.services import (
    WebScraperService,
    ScraperService,
    ScraperComparisonService,
)
from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.utils.notify_change import check_new_species_and_notify
import logging
from django.utils import timezone
from datetime import datetime, date

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def scraper_url_task(self, url):


    scraper_service = WebScraperService()

    try:
        scraper_url = ScraperURL.objects.get(url=url)
        sobrenombre = scraper_url.sobrenombre

        logger.info(f"📌 Tipo de fecha_scraper antes de conversión: {type(scraper_url.fecha_scraper)}")

        if isinstance(scraper_url.fecha_scraper, datetime):
            if timezone.is_naive(scraper_url.fecha_scraper):
                scraper_url.fecha_scraper = timezone.make_aware(scraper_url.fecha_scraper, timezone.get_current_timezone())
        elif isinstance(scraper_url.fecha_scraper, date): 
            scraper_url.fecha_scraper = datetime.combine(scraper_url.fecha_scraper, datetime.min.time())
            scraper_url.fecha_scraper = timezone.make_aware(scraper_url.fecha_scraper, timezone.get_current_timezone())
        else:
            logger.error(f"⚠️ Tipo inesperado en fecha_scraper: {type(scraper_url.fecha_scraper)}")
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
    else:
        logger.info(f"Task {self.request.id}: Scraping exitoso para {url}, iniciando flujo de procesamiento...")
        tarea_encadenada = chain(
            process_scraped_data_task.s(url), generate_comparison_report_task.si(url)
        )
        tarea_encadenada.apply_async()
        return {"status": "success", "url": url}



@shared_task(bind=True)
def process_scraped_data_task(self, url):
    if not url:
        logger.error("No se recibió una URL válida en process_scraped_data_task")
        return None

    scraper = ScraperService()
    scraper.extract_and_save_species(url)
    check_new_species_and_notify([url])

    return url


@shared_task(bind=True)
def generate_comparison_report_task(self, url):
    if not url:
        logger.error("No se recibió una URL válida en generate_comparison_report_task")
        return None

    comparison_service = ScraperComparisonService()
    result = comparison_service.get_comparison_for_url(url)

    if result.get("status") == "no_comparison":
        logger.info(f"No hay suficientes registros para comparación en la URL: {url}")
        return None

    elif result.get("status") == "missing_content":
        logger.warning(f"Uno de los registros de {url} no tiene contenido para comparar.")
        return None

    elif result.get("status") == "duplicate":
        logger.info(f"La comparación entre las versiones ya existe y no ha cambiado para la URL {url}")
        return None

    # Si hay cambios, devolver el resultado sin notificar a los usuarios
    logger.info(f"Reporte de comparación generado o actualizado para {url}: {result}")

    return result  # ✅ Solo devolver los cambios detectados



@shared_task(bind=True)
def scraper_expired_urls_task(self):
    scraper_service = WebScraperService()
    urls = scraper_service.get_expired_urls()

    if not urls:
        logger.info("No hay URLs expiradas para scrapear.")
        return

    for url in urls:
        chain(
            scraper_url_task.s(url),
            process_scraped_data_task.s(url),
            generate_comparison_report_task.si(url),
        ).apply_async()

    logger.info(
        f"Scraping, conversión y comparación secuencial iniciada para {len(urls)} URLs."
    )


@shared_task(bind=True)
def check_species_for_selected_urls_task(self):
    urls_para_revisar = list(ScraperURL.objects.filter(is_active=True).values_list("url", flat=True))

    if not urls_para_revisar:
        logger.info("No hay URLs activas para verificar.")
        return

    for url in urls_para_revisar:
        process_scraped_data_task.delay(url)
