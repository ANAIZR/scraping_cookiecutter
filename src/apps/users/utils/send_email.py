from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from email.mime.image import MIMEImage
import os


def send_welcome_email(user):
    subject = "Bienvenido al portal de WEB SCRAPER"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]

    html_content = f"""
    <html>
        <body style="background-color: #f0f0f0; padding: 20px; font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <!-- Encabezado -->
                <div style="background-color: #f0f0f0; text-align: center; padding: 20px;">
                    <img src="cid:logo_stdf" alt="Encabezado" style="max-width: 100%; height: auto;">
                </div>

                <!-- Cuerpo del correo -->
                <div style="padding: 20px; background-color: white;">
                    <h1 style="color: #333; text-align: center;">¡Bienvenido, {user.email}!</h1>
                    <p style="color: #555;">Gracias por registrarte en la plataforma de <strong>WEB SCRAPER</strong>.</p>
                    <p style="color: #555; text-align: center;">Para ingresar al sistema haz clic en el siguiente enlace:</p>
                    <p style="text-align: center;">
                        <a href="http://localhost:3000" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ingresar</a>
                    </p>
                    <p style="color: #555; text-align: center; margin-top: 20px;">¡Gracias por unirte a nosotros!</p>
                </div>

                <!-- Pie de página -->
                <div style="background-color: #f0f0f0; text-align: center; padding: 20px;">
                    <p style="color: #777; font-size: 12px;">No responda a este correo, ha sido generado automáticamente.</p>
                </div>
            </div>
        </body>
    </html>
    """

    # Crear el correo con EmailMultiAlternatives
    email = EmailMultiAlternatives(subject, "", from_email, recipient_list)
    email.attach_alternative(html_content, "text/html")
    email.mixed_subtype = "related"

    # Ruta de la imagen del encabezado
    img_path = os.path.join(
        settings.BASE_DIR,
        "src",
        "apps",
        "core",
        "static",
        "images",
        "Logo_STDF_S_H.png",
    )

    with open(img_path, "rb") as img:
        mime_image = MIMEImage(img.read())
        mime_image.add_header("Content-ID", "<logo_stdf>")
        mime_image.add_header(
            "Content-Disposition", "inline", filename="Logo_STDF_S_H.png"
        )
        email.attach(mime_image)

    # Enviar el correo
    email.send()
