from src.apps.shared.models.scraperURL import ScraperURL, NotificationSubscription
import logging
from src.apps.users.utils.services import EmailService
logger = logging.getLogger(__name__)




def notify_users_of_changes(url, comparison_result):
    try:
        scraper_url = ScraperURL.objects.get(url=url)
        subscribers = NotificationSubscription.objects.filter(scraper_url=scraper_url)

        if not subscribers.exists():
            logger.info(f"No hay usuarios suscritos para recibir notificaciones de la URL {url}.")
            return

        recipient_list = [sub.user.email for sub in subscribers]

        subject = "🔔 Se detectaron cambios en la página que monitoreas"
        html_content = f"""
            <p>Se han detectado cambios en la siguiente URL:</p>
            <a href="{url}">{url}</a>
            <p>Resumen de cambios:</p>
            <pre>{comparison_result.get("summary", "No disponible")}</pre>
            <p>Revisa las actualizaciones en la plataforma.</p>
        """

        EmailService.send_email(subject, recipient_list, html_content)
        logger.info(f"Correo de notificación enviado a {len(recipient_list)} usuarios suscritos a {url}.")

    except ScraperURL.DoesNotExist:
        logger.error(f"No se encontró ScraperURL para la URL {url}, no se enviará la notificación.")
