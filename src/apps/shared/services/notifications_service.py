from src.apps.shared.models.species import SpeciesSubscription, SpeciesNews
import logging
from django.utils import timezone
from datetime import timedelta
from src.apps.users.services.email import EmailService

logger = logging.getLogger(__name__)

class SpeciesNotificationService:
    def __init__(self):
        self.now = timezone.now()
        self.last_scraping_time = self.now - timedelta(hours=1)  # Busca noticias en la última hora

    def check_new_news_and_notify(self):

        new_news = SpeciesNews.objects.filter(
            publication_date__gte=self.last_scraping_time  # Busca noticias recientes
        )

        if not new_news.exists():
            return  

        # Obtener suscripciones con el mismo `scientific_name` que las noticias
        subscriptions = SpeciesSubscription.objects.filter(
            scientific_name__in=new_news.values_list("scientific_name", flat=True)
        )

        for subscription in subscriptions:
            user = subscription.user
            matched_news = new_news.filter(scientific_name=subscription.scientific_name)

            if matched_news.exists():
                self.notify_user_of_new_news(user, subscription, matched_news)
                subscription.last_notified_at = timezone.now()  # Actualiza última notificación
                subscription.save()

    def notify_user_of_new_news(self, user, subscription, news):
        """Envía un correo al usuario notificando sobre nuevas noticias"""

        subject = f"📰 Nuevas noticias sobre {subscription.scientific_name}"
        news_list = "".join(
            f"<li>{n.publication_date}: <a href='{n.source_url}'>{n.summary}</a></li>" for n in news
        )

        html_content = f"""
            <p>Se han detectado <b>{len(news)} nuevas noticias</b> sobre <b>{subscription.scientific_name}</b>.</p>
            <p><b>Detalles:</b></p>
            <ul>{news_list}</ul>
            <p>Revisa las nuevas actualizaciones en la plataforma.</p>
        """

        EmailService.send_email(subject, [user.email], html_content)