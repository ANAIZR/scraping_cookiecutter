from celery import shared_task
from src.apps.users.utils.services import UserService, EmailService

import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_password_reset_email_task(self, email):
    result = UserService.send_password_reset_email(email)

    if "error" in result:
        logger.error(f"Error en envío de correo: {result['error']}")

    return result


@shared_task(bind=True)
def reset_password_task(self, email, token, new_password):
    result = UserService.reset_password(email, token, new_password)

    if "error" in result:
        logger.error(f"Error al restablecer la contraseña: {result['error']}")

    return result


@shared_task(bind=True)
def soft_delete_user_task(self, user_id):
    from src.apps.users.models import User

    try:
        user = User.objects.get(id=user_id)
        UserService.soft_delete_user(user)
    except User.DoesNotExist:
        logger.error(f"Usuario con ID {user_id} no encontrado.")


@shared_task(bind=True)
def send_email_task(self, subject, recipient_list, html_content):
    result = EmailService.send_email(subject, recipient_list, html_content)

    if "error" in result:
        logger.error(f"Error al enviar correo: {result['error']}")

    return result
@shared_task
def send_welcome_email_task(email):
    UserService.send_welcome_email(email)