from celery import shared_task
from src.apps.shared.services.report_compare import ScraperComparisonService
import logging


logger = logging.getLogger(__name__)



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
