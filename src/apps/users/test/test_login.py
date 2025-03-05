
import pytest
from unittest.mock import patch
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from src.apps.users.models import User
from src.apps.shared.api.serializers.login_serializers import LoginSerializer
from rest_framework import status
from rest_framework.test import APIClient

LOGIN_URL = reverse("login") 

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_login_success():
    user = User.objects.create(
        email="user@example.com",
        username="testuser",
        last_name="TestLast",
        password=make_password("securepassword"), 
        is_active=True
    )

    data = {"email": "user@example.com", "password": "securepassword"}
    serializer = LoginSerializer(data=data)

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["user"] == user


@pytest.mark.django_db
def test_login_user_not_found():
    data = {"email": "notfound@example.com", "password": "wrongpassword"}
    serializer = LoginSerializer(data=data)

    assert not serializer.is_valid()
    assert "Usuario no encontrado." in str(serializer.errors)


@pytest.mark.django_db
def test_login_invalid_password():
    User.objects.create(
        email="user@example.com",
        password=make_password("securepassword"),
        is_active=True
    )

    data = {"email": "user@example.com", "password": "wrongpassword"}
    serializer = LoginSerializer(data=data)

    assert not serializer.is_valid()
    assert "Datos invalidos" in str(serializer.errors)


@pytest.mark.django_db
def test_login_inactive_user():
    User.objects.create(
        email="user@example.com",
        password=make_password("securepassword"),
        is_active=False  
    )

    data = {"email": "user@example.com", "password": "securepassword"}
    serializer = LoginSerializer(data=data)

    assert not serializer.is_valid()
    assert "El usuario no está activo." in str(serializer.errors)


@pytest.mark.django_db
def test_login_missing_email_or_password():
    data = {"email": "user@example.com"}  
    serializer = LoginSerializer(data=data)

    assert not serializer.is_valid()
    assert "Debe incluir tanto 'email' como 'password'." in str(serializer.errors)


@pytest.mark.django_db
def test_login_success(api_client, test_user):
    response = api_client.post(LOGIN_URL, {"email": "test@example.com", "password": "securepassword"})
    
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


@pytest.mark.django_db
def test_login_invalid_credentials(api_client):
    response = api_client.post(LOGIN_URL, {"email": "wrong@example.com", "password": "wrongpassword"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Usuario no encontrado." in response.json()["non_field_errors"]


@pytest.mark.django_db
def test_login_inactive_user(api_client, inactive_user):
    response = api_client.post(LOGIN_URL, {"email": "inactive@example.com", "password": "securepassword"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "El usuario no está activo." in response.json()["non_field_errors"]