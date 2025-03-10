from apps.shared.models.species import SpeciesSubscription, Species
import logging
from django.utils import timezone
from datetime import timedelta
from src.apps.users.services.email import EmailService

logger = logging.getLogger(__name__)

class SpeciesNotificationService:

    def __init__(self):
        self.now = timezone.now()
        self.last_scraping_time = self.now - timedelta(hours=1)  

    def check_new_species_and_notify(self, urls_to_check):

        new_species = Species.objects.filter(
            created_at__gte=self.last_scraping_time,
            scraper_source__url__in=urls_to_check  
        )

        if not new_species.exists():
            return  

        subscriptions = SpeciesSubscription.objects.filter(
            scientific_name__in=new_species.values_list("scientific_name", flat=True)
        )

        for subscription in subscriptions:
            user = subscription.user
            matched_species = self.filter_species_by_subscription(new_species, subscription)

            if matched_species.exists():
                self.notify_user_of_new_species(user, subscription, matched_species)

    def filter_species_by_subscription(self, new_species, subscription):

        if subscription.scientific_name:
            new_species = new_species.filter(scientific_name__icontains=subscription.scientific_name)
        if subscription.distribution:
            new_species = new_species.filter(distribution__icontains=subscription.distribution)
        if subscription.hosts:
            new_species = new_species.filter(hosts__icontains=subscription.hosts)
        return new_species

    def notify_user_of_new_species(self, user, subscription, species):

        filters = []
        if subscription.scientific_name:
            filters.append(f"Nombre Científico: {subscription.scientific_name}")
        if subscription.distribution:
            filters.append(f"Distribución: {subscription.distribution}")
        if subscription.hosts:
            filters.append(f"Hospedante: {subscription.hosts}")

        filters_text = "<br>".join(filters)
        subject = f"🔔 Se han añadido {len(species)} nuevos registros para tu filtro guardado"

        species_list = "".join(f"<li>{s.scientific_name} - {s.source_url}</li>" for s in species)

        html_content = f"""
            <p>Se han detectado <b>{len(species)} nuevos registros</b> que coinciden con tu filtro guardado.</p>
            <p><b>Filtros:</b></p>
            <p>{filters_text}</p>
            <p><b>Detalles:</b></p>
            <ul>{species_list}</ul>
            <p>Revisa las nuevas actualizaciones en la plataforma.</p>
        """

        EmailService.send_email(subject, [user.email], html_content)
