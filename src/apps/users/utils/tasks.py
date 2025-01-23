from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
import os
from django.conf import settings

@shared_task
def send_email_task(subject, recipient_list, html_content):
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

    with open(img_path, "rb") as img:
        mime_image = MIMEImage(img.read())
        mime_image.add_header("Content-ID", "<logo_stdf>")
        mime_image.add_header(
            "Content-Disposition", "inline", filename="Logo_STDF_S_H.png"
        )
        email.attach(mime_image)

    email.send()
