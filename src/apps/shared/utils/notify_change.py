from src.apps.shared.models.scraperURL import ScraperURL, NotificationSubscription, SpeciesSubscription, Species
import logging
from django.utils import timezone
from datetime import timedelta
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


def check_new_species_and_notify():

    now = timezone.now()
    last_scraping_time = now - timedelta(hours=1)  

    new_species = Species.objects.filter(created_at__gte=last_scraping_time)

    if not new_species.exists():
        return  

    subscriptions = SpeciesSubscription.objects.all()

    for subscription in subscriptions:
        user = subscription.user
        scientific_name = subscription.scientific_name
        distribution = subscription.distribution
        hosts = subscription.hosts

        matched_species = new_species
        if scientific_name:
            matched_species = matched_species.filter(scientific_name__icontains=scientific_name)
        if distribution:
            matched_species = matched_species.filter(distribution__icontains=distribution)
        if hosts:
            matched_species = matched_species.filter(hosts__icontains=hosts)

        if matched_species.exists():
            notify_user_of_new_species(user, subscription, matched_species)

def notify_user_of_new_species(user, subscription, species):

    filters = []
    if subscription.scientific_name:
        filters.append(f"Nombre Científico: {subscription.scientific_name}")
    if subscription.distribution:
        filters.append(f"Distribución: {subscription.distribution}")
    if subscription.hosts:
        filters.append(f"Hospedante: {subscription.hosts}")

    filters_text = "<br>".join(filters)

    subject = f"🔔 Se han añadido {species.count()} nuevos registros para tu filtro guardado"

    species_list = "".join(f"<li>{s.scientific_name} - {s.source_url}</li>" for s in species)

    html_content = f"""
        <p>Se han detectado <b>{species.count()} nuevos registros</b> que coinciden con tu filtro guardado.</p>
        <p><b>Filtros:</b></p>
        <p>{filters_text}</p>
        <p><b>Detalles:</b></p>
        <ul>{species_list}</ul>
        <p>Revisa las nuevas actualizaciones en la plataforma.</p>
    """

    EmailService.send_email(subject, [user.email], html_content)