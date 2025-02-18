import os
import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from email.mime.image import MIMEImage
from src.apps.users.models import User
from django.utils import timezone
from django.core.cache import cache
import random

logger = logging.getLogger(__name__)


class EmailService:
    @classmethod
    def send_welcome_email(cls, email, username):
        from src.apps.users.utils.tasks import send_welcome_email_task
        subject = "Bienvenido al portal de WEB SCRAPER"
        recipient_list = [email]

        html_content = f"""
        <html>
            <body style="background-color: #f0f0f0; padding: 20px; font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                    <div style="background-color: #f0f0f0; text-align: center; padding: 20px;">
                        <img src="cid:logo_stdf" alt="Encabezado" style="max-width: 100%; height: auto;">
                    </div>
                    <div style="padding: 20px; background-color: white;">
                        <h1 style="color: #333; text-align: center;">¡Bienvenido, {username}!</h1>
                        <p style="color: #555;">Gracias por registrarte en la plataforma de <strong>WEB SCRAPER</strong>.</p>
                        <p style="color: #555; text-align: center;">Para ingresar al sistema haz clic en el siguiente enlace:</p>
                        <p style="text-align: center;">
                            <a href="{settings.FRONTEND_URL}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ingresar</a>
                        </p>
                        <p style="color: #555; text-align: center; margin-top: 20px;">¡Gracias por unirte a nosotros!</p>
                    </div>
                    <div style="background-color: #f0f0f0; text-align: center; padding: 20px;">
                        <p style="color: #777; font-size: 12px;">No responda a este correo, ha sido generado automáticamente.</p>
                    </div>
                </div>
            </body>
        </html>
        """

        send_welcome_email_task.delay(subject, recipient_list, html_content)
        
        logger.info(f"Correo de bienvenida programado para {email}")
    @staticmethod
    def send_email(subject, recipient_list, html_content):
        from_email = settings.EMAIL_HOST_USER

        email = EmailMultiAlternatives(subject, "", from_email, recipient_list)
        email.attach_alternative(html_content, "text/html")
        email.mixed_subtype = "related"

        img_path = os.path.join(
            settings.BASE_DIR,
            "src",
            "apps",
            "core",
            "static",
            "images",
            "Logo_STDF_S_H.png",
        )

        try:
            with open(img_path, "rb") as img:
                mime_image = MIMEImage(img.read())
                mime_image.add_header("Content-ID", "<logo_stdf>")
                mime_image.add_header("Content-Disposition", "inline", filename="Logo_STDF_S_H.png")
                email.attach(mime_image)

            email.send()
            return {"success": True, "message": "Correo enviado correctamente"}
        except Exception as e:
            logger.error(f"Error enviando correo: {str(e)}")
            return {"success": False, "error": str(e)}


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
