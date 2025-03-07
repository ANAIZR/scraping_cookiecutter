
import logging
from .email import EmailService
from src.apps.users.models import User
from django.utils import timezone
from django.core.cache import cache
import random

logger = logging.getLogger(__name__)

class UserService:
    
    @staticmethod
    def send_password_reset_email(email):
        try:
            user = User.objects.get(email=email)
            token = "{:06d}".format(random.randint(0, 999999))
            cache.set(f"password_reset_{email}", token, timeout=600)

            subject = "Restablecimiento de Contraseña"
            message = f"Tu token de restablecimiento de contraseña es: {token}"

            EmailService.send_email(subject, [user.email], message)

            return {"message": "Código de restablecimiento enviado."}
        except User.DoesNotExist:
            return {"error": "El correo electrónico no está registrado."}

    @staticmethod
    def reset_password(email, token, new_password):
        try:
            user = User.objects.get(email=email)
            cached_token = cache.get(f"password_reset_{email}")

            if cached_token != token:
                return {"error": "Token inválido o ha expirado."}

            cache.delete(f"password_reset_{email}")
            user.set_password(new_password)
            user.save()

            return {"message": "La contraseña ha sido restablecida exitosamente."}
        except User.DoesNotExist:
            return {"error": "Usuario no encontrado."}
    @staticmethod
    def is_valid_reset_token(email, token):

        cached_token = cache.get(f"password_reset_{email}")
        return cached_token == token 

    @staticmethod
    def soft_delete_user(user):
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save()
        logger.info(f"Usuario {user.username} desactivado correctamente.")

    @staticmethod
    def restore_user(user):
        if user.deleted_at is not None:  
            user.restore()
            logger.info(f"Usuario {user.username} restaurado correctamente.")
        else:
            logger.warning(f"El usuario {user.username} ya estaba activo.")
    @staticmethod
    def update_system_role(user: User):
        if user.system_role == 1:
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_staff = False
            user.is_superuser = False
        
        user.save()  # Asegura que se guarde el cambio
        logger.info(f"✅ Rol del usuario {user.username} actualizado a {user.system_role}")
