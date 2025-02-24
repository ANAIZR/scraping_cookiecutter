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


from celery import chain

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def scraper_url_task(self, url, manual=False):
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
        return None  

    except Exception as e:
        logger.error(f"Task {self.request.id}: Error al actualizar fecha de scraping para {url}: {str(e)}")
        return None  

    result = scraper_service.scraper_one_url(url, sobrenombre)

    if "error" in result:
        logger.error(f"Task {self.request.id}: Scraping fallido para {url}: {result['error']}")
        scraper_url.estado_scrapeo = "fallido"
        scraper_url.error_scrapeo = result["error"]
        scraper_url.save()
        return None  

    logger.info(f"Task {self.request.id}: Scraping exitoso para {url}")
    scraper_url.estado_scrapeo = "exitoso"
    scraper_url.error_scrapeo = ""
    scraper_url.save()

    if manual:
        return chain(
            process_scraped_data_task.s(url),
            generate_comparison_report_task.si(url),
        ).apply_async()

    return url  


URLS_PERMITIDAS = {
    "https://www.ippc.int/en/countries/south-africa/pestreports/",
    "https://www.pestalerts.org/nappo/emerging-pest-alerts/",
}

@shared_task(bind=True)
def process_scraped_data_task(self, url, previous_result=None): 
    if not url:
        logger.warning(f"Task {self.request.id}: URL vacía o fallida, no se procesará.")
        return None 

    scraper = ScraperService()
    scraper.extract_and_save_species(url)

    if url in URLS_PERMITIDAS:
        check_new_species_and_notify([url])

    return url  





@shared_task(bind=True)
def generate_comparison_report_task(self, url):

    if not url:
        logger.error(
            "❌ No se recibió una URL válida en generate_comparison_report_task"
        )
        return {"status": "error", "message": "URL inválida"}

    try:
        comparison_service = ScraperComparisonService()
        result = comparison_service.get_comparison_for_url(url)

        if result.get("status") == "no_comparison":
            logger.info(
                f"🔍 No hay suficientes registros para comparar en la URL: {url}"
            )
            return result

        elif result.get("status") == "missing_content":
            logger.warning(
                f"⚠️ Uno de los registros de {url} no tiene contenido para comparar."
            )
            return result

        elif result.get("status") == "duplicate":
            logger.info(
                f"✅ La comparación entre versiones ya existe y no ha cambiado para la URL {url}"
            )
            return result

        if result.get("status") == "changed":
            logger.info(f"📊 Se generó un nuevo reporte de comparación para {url}:")
            logger.info(f"🔹 Nuevas URLs: {result.get('info_agregada', [])}")
            logger.info(f"🔸 URLs Eliminadas: {result.get('info_eliminada', [])}")
            logger.info(
                f"📌 Estructura cambiada: {result.get('estructura_cambio', False)}"
            )

        return result

    except Exception as e:
        logger.error(
            f"❌ Error en generate_comparison_report_task para {url}: {str(e)}",
            exc_info=True,
        )
        return {"status": "error", "message": f"Error interno: {str(e)}"}


@shared_task(bind=True)
def scraper_expired_urls_task(self):
    scraper_service = WebScraperService()
    urls = scraper_service.get_expired_urls()

    if not urls:
        logger.info("No hay URLs expiradas para scrapear.")
        return

    full_chain = scraper_url_task.s(urls[0]) | process_scraped_data_task.s(urls[0]) | generate_comparison_report_task.si(urls[0])

    for url in urls[1:]:
        next_chain = scraper_url_task.s(url) | process_scraped_data_task.s(url) | generate_comparison_report_task.si(url)
        full_chain |= next_chain 

    if full_chain:
        full_chain.apply_async(link_error=handle_task_error.s())

    logger.info(f"Scraping en secuencia iniciado para {len(urls)} URLs.")


@shared_task
def handle_task_error(request=None, exc=None, traceback=None, *args, **kwargs):
    task_name = request.task if request and hasattr(request, "task") else "Tarea desconocida"
    logger.error(f"Error en {task_name}: {exc}")
