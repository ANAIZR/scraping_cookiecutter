from src.apps.users.utils.tasks import send_email_task

def send_welcome_email(user):
    subject = "Bienvenido al portal de WEB SCRAPER"
    recipient_list = [user.email]

    html_content = f"""
    <html>
        <body style="background-color: #f0f0f0; padding: 20px; font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
                <div style="background-color: #f0f0f0; text-align: center; padding: 20px;">
                    <img src="cid:logo_stdf" alt="Encabezado" style="max-width: 100%; height: auto;">
                </div>
                <div style="padding: 20px; background-color: white;">
                    <h1 style="color: #333; text-align: center;">¡Bienvenido, {user.email}!</h1>
                    <p style="color: #555;">Gracias por registrarte en la plataforma de <strong>WEB SCRAPER</strong>.</p>
                    <p style="color: #555; text-align: center;">Para ingresar al sistema haz clic en el siguiente enlace:</p>
                    <p style="text-align: center;">
                        <a href="http://localhost:3000" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ingresar</a>
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

    send_email_task.delay(subject, recipient_list, html_content)
