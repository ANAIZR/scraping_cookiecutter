from celery import shared_task
from django.utils.timezone import now
from src.apps.users.models import User
import logging

logger = logging.getLogger(__name__)

@shared_task
def renew_access_token():

    try:
        user = User.objects.filter(is_active=True).first()  
        if not user:
            logger.error("No se encontró un usuario activo.")
            return {"status": "error", "message": "No se encontró un usuario activo."}

        new_token = "nuevo_token_generado"  
        user.access_token = new_token
        user.save()

        logger.info(f"Token actualizado para el usuario {user.username}")
        return {"status": "success", "message": f"Token actualizado para {user.username}"}
    except Exception as e:
        logger.error(f"Error al renovar el token: {str(e)}")
        return {"status": "error", "message": f"Error al renovar el token: {str(e)}"}
