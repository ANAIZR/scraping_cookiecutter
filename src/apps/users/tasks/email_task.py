
from celery import shared_task
from src.apps.users.services.email import  EmailService

import logging
logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_email_task(self, subject, recipient_list, html_content):
    result = EmailService.send_email(subject, recipient_list, html_content)

    if "error" in result:
        logger.error(f"Error al enviar correo: {result['error']}")

    return result
@shared_task
def send_welcome_email_task(email, username):
    EmailService.send_welcome_email(email, username)
