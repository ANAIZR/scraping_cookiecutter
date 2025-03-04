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
        UserService.soft_delete_user(user) 
        logger.info(f"✅ Usuario {user.username} desactivado correctamente.")
    except User.DoesNotExist:
        logger.error(f"❌ Usuario con ID {user_id} no encontrado.")
    except Exception as e:
        logger.error(f"❌ Error en soft_delete_user_task: {str(e)}")


@shared_task
def restore_user_task(user_id):
    try:
        user = User.objects.get(id=user_id)
        UserService.restore_user(user) 
        logger.info(f"✅ Usuario {user.username} restaurado correctamente.")
    except User.DoesNotExist:
        logger.error(f"❌ Usuario con ID {user_id} no encontrado.")
    except Exception as e:
        logger.error(f"❌ Error en restore_user_task: {str(e)}")


@shared_task(bind=True)
def send_email_task(self, subject, recipient_list, html_content):
    result = EmailService.send_email(subject, recipient_list, html_content)

    if "error" in result:
        logger.error(f"Error al enviar correo: {result['error']}")

    return result
@shared_task
def send_welcome_email_task(email, username):
    EmailService.send_welcome_email(email, username)
@shared_task
def update_system_role_task(user_id):
    try:
        user = User.objects.get(id=user_id)

        if user.is_superuser and user.system_role != 1:
            user.system_role = 1
            user.save()
            return
        
        UserService.update_system_role(user)
    
    except User.DoesNotExist:
        logger.error(f"❌ Usuario con ID {user_id} no encontrado. Cancelando tarea.")
    except Exception as e:
        logger.error(f"❌ Error en update_system_role_task: {str(e)}")
