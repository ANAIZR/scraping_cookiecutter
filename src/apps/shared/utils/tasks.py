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

logger = logging.getLogger(__name__)

from celery import chain


@shared_task(bind=True)
def scraper_url_task(self, url):
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
        logger.error(
            f"Task {self.request.id}: Error al actualizar fecha de scraping para {url}: {str(e)}"
        )
        return {"status": "failed", "url": url, "error": str(e)}

    result = scraper_service.scraper_one_url(url, sobrenombre)

    if "error" in result:
        logger.error(
            f"Task {self.request.id}: Scraping fallido para {url}: {result['error']}"
        )
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
def check_new_species_task(self, urls):
    check_new_species_and_notify(urls)


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

    try:
        logger.info(f"Iniciando scraping en secuencia para {len(urls)} URLs...")

        task_chain = chain(*[scraper_url_task.si(url) for url in urls])
        task_chain.apply_async()

        logger.info("Tareas encoladas en secuencia.")
    except Exception as e:
        logger.error(f"Error al encolar scraper en secuencia: {str(e)}")
