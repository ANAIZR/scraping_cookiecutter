from celery import shared_task
import requests
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task
def renew_access_token():
    user = User.objects.filter(system_role=1).first()  # Administrador
    if not user:
        raise Exception(
            "No se encontró un usuario administrador para renovar el token."
        )

    login_data = {
        "email": "admin@gmail.com",
        "password": "admin",
    }

    response = requests.post(
        "http://127.0.0.1:8000/api/v1/login/",
        data=login_data,
    )

    if response.status_code == 200:
        data = response.json()
        user.access_token = data["access_token"]
        user.save()
        print("Token renovado correctamente.")
    else:
        print(f"Error al renovar el token: {response.status_code} - {response.text}")
