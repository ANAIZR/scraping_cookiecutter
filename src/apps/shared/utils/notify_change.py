from src.apps.shared.models.scraperURL import SpeciesSubscription, Species
import logging
from django.utils import timezone
from datetime import timedelta
from src.apps.users.utils.services import EmailService
logger = logging.getLogger(__name__)



def check_new_species_and_notify(urls_to_check):

    now = timezone.now()
    last_scraping_time = now - timedelta(hours=1)  

    new_species = Species.objects.filter(
        created_at__gte=last_scraping_time,
        scraper_source__url__in=urls_to_check  
    )

    if not new_species.exists():
        return  

    subscriptions = SpeciesSubscription.objects.filter(
        scientific_name__in=new_species.values_list("scientific_name", flat=True)
    )

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