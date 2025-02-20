from celery import shared_task, chain
from src.apps.shared.utils.services import WebScraperService, ScraperService, ScraperComparisonService
from src.apps.shared.models.scraperURL import ScraperURL
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


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
        return None

    logger.info(f"Scraping exitoso para {url}, iniciando flujo de procesamiento...")

    tarea_encadenada = chain(
        process_scraped_data_task.s(url), 
        generate_comparison_report_task.si(url)  
    )

    tarea_encadenada.apply_async()

    return url


@shared_task(bind=True)
def process_scraped_data_task(self, url): 
    if not url:
        logger.error("No se recibió una URL válida en process_scraped_data_task")
        return None

    scraper = ScraperService()
    scraper.extract_and_save_species(url)

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
    elif result.get("status") == "missing_content":
        logger.warning(f"Uno de los registros de {url} no tiene contenido para comparar.")
    else:
        logger.info(f"Reporte de comparación generado o actualizado para {url}: {result}")

    return result


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
            generate_comparison_report_task.si(url)  
        ).apply_async()

    logger.info(f"Scraping, conversión y comparación secuencial iniciada para {len(urls)} URLs.")
