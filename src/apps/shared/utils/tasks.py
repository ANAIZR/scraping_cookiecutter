from celery import shared_task, chain
from src.apps.shared.utils.services import WebScraperService, ScraperService, ScraperComparisonService
from src.apps.shared.models.scraperURL import ScraperURL
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from celery import chain


@shared_task(bind=True)
def scraper_expired_urls_task(self):

    scraper_service = WebScraperService()
    urls = scraper_service.get_expired_urls()

    if not urls:
        logger.info("No hay URLs expiradas para scrapear.")
        return

    # 🔹 Ejecuta cada URL en secuencia: Scraping → Guardado en PostgreSQL → Comparación
    tareas_encadenadas = chain(
        *[scraper_url_task.s(url) | run_scraper_task.s() | compare_scraped_content_task.s(url) for url in urls]
    )
    tareas_encadenadas.apply_async()

    logger.info(f"Scraping en secuencia iniciado para {len(urls)} URLs.")


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
    else:
        logger.info(f"Scraping exitoso para {url}, iniciando flujo de procesamiento...")

        tarea_encadenada = chain(
            run_scraper_task.s(url),
            compare_scraped_content_task.s(url)
        )
        tarea_encadenada.apply_async()

    return result



@shared_task(bind=True)
def run_scraper_task(self, url):

    scraper_service = ScraperService()
    scraper_service.extract_and_save_species(url)

    logger.info(f"Datos procesados y guardados en PostgreSQL para la URL: {url}")

    return url  # Devuelve la URL para continuar con la comparación

@shared_task(bind=True)
def compare_scraped_content_task(self, url):
    
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

    tarea_encadenada = chain(*[
        scraper_url_task.s(url) | run_scraper_task.s(url) | compare_scraped_content_task.s(url)
        for url in urls
    ])
    tarea_encadenada.apply_async()

    logger.info(f"Scraping, conversión y comparación secuencial iniciada para {len(urls)} URLs.")
