from celery import shared_task
from src.apps.users.utils.services import UserService, EmailService
from src.apps.users.models import User
import logging
from django.utils import timezone
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

@shared_task
def soft_delete_user_task(user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save()
        logger.info(f"Usuario {user.username} desactivado correctamente.")
    except User.DoesNotExist:
        logger.error(f"Usuario con ID {user_id} no encontrado.")
    except Exception as e:
        logger.error(f"Error en soft_delete_user_task: {str(e)}")


def restore_user_task(user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.deleted_at = None
        user.save()
        logger.info(f"Usuario {user.username} restaurado correctamente.")
    except User.DoesNotExist:
        logger.error(f"Usuario con ID {user_id} no encontrado.")
    except Exception as e:
        logger.error(f"Error en restore_user_task: {str(e)}")

@shared_task(bind=True)
def send_email_task(self, subject, recipient_list, html_content):
    result = EmailService.send_email(subject, recipient_list, html_content)

    if "error" in result:
        logger.error(f"Error al enviar correo: {result['error']}")

    return result
@shared_task
def send_welcome_email_task(email):
    EmailService.send_welcome_email(email)
@shared_task(bind=True)
def update_system_role_task(self, user_id):
    try:
        user = User.objects.get(id=user_id)

        if user.system_role == 1:
            user.is_superuser = True
            user.is_staff = True
        else:
            user.is_superuser = False
            user.is_staff = False

        user.save()
        logger.info(f"Rol del usuario {user.username} actualizado correctamente.")
    except User.DoesNotExist:
        logger.error(f"Usuario con ID {user_id} no encontrado.")
    except Exception as e:
        logger.error(f"Error al actualizar rol del usuario {user_id}: {str(e)}")