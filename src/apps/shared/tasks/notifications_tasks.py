from celery import shared_task
from src.apps.shared.services.notifications import SpeciesNotificationService
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def check_new_species_task(self, urls, *args, **kwargs):

    notification_service = SpeciesNotificationService()  
    notification_service.check_new_species_and_notify(urls) 
