import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient
from src.apps.users.models import User
from src.apps.users.utils.tasks import update_system_role_task, soft_delete_user_task
from src.apps.users.utils.services import UserService
from src.apps.users.api.serializers import UsuarioGETSerializer, UsuarioPOSTSerializer, PasswordResetRequestSerializer, PasswordResetSerializer

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        username="admin_user",
        email="admin@example.com",
        password="adminpass"
    )
    user.system_role = 1 
    user.save()
    return user

@pytest.fixture
def funcionario_user(db):
    return User.objects.create_user(
        username="funcionario_user",
        email="funcionario@example.com",
        password="funcionariopass",
        system_role=2  
    )

@pytest.fixture
def user_factory(db):
    def create_user(username, email, password="securepassword", system_role=2):
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            system_role=system_role
        )
    return create_user

@pytest.fixture
def test_user(db): 
    return User.objects.create_user(
        username="user_test",
        email="test_user@example.com",
        password="testpass",
        system_role=2  
    )
@pytest.mark.django_db(transaction=True)
@patch("src.apps.users.utils.tasks.send_welcome_email_task.apply_async")
@patch("src.apps.users.utils.tasks.update_system_role_task.apply_async")
def test_admin_can_create_user(mock_update_role, mock_send_email, api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.post("/api/users/", {
        "username": "newuser",
        "last_name": "UserLastName",
        "email": "new@example.com",
        "password": "securepassword",
        "system_role": 2
    })

    assert response.status_code == 201
    mock_send_email.assert_called_once()
    mock_update_role.assert_called_once()

@pytest.mark.django_db
def test_non_admin_cannot_create_user(api_client, funcionario_user):
    api_client.force_authenticate(user=funcionario_user)

    response = api_client.post("/api/users/", {
        "username": "newuser",
        "email": "new@example.com",
        "password": "securepassword",
        "system_role": 2
    })

    assert response.status_code == 403
    assert not User.objects.filter(username="newuser").exists()

@pytest.mark.django_db
def test_admin_can_update_user(api_client, admin_user, test_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(f"/api/users/{test_user.id}/", {"username": "updated_user"})

    assert response.status_code == 200
    test_user.refresh_from_db()
    assert test_user.username == "updated_user"

@pytest.mark.django_db
def test_non_admin_cannot_update_user(api_client, funcionario_user, test_user):
    api_client.force_authenticate(user=funcionario_user)

    response = api_client.patch(f"/api/users/{test_user.id}/", {"username": "updated_user"})

    assert response.status_code == 403
    test_user.refresh_from_db()
    assert test_user.username == "user_test"

@patch("src.apps.users.api.views.soft_delete_user_task.apply_async")
@pytest.mark.django_db
def test_admin_can_delete_user(mock_soft_delete, api_client, admin_user, test_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.delete(f"/api/users/{test_user.id}/")

    assert response.status_code == 204

    print(mock_soft_delete.call_args_list)  

    mock_soft_delete.assert_called_once_with(test_user.id)

    soft_delete_user_task(test_user.id)

    test_user.refresh_from_db()
    assert test_user.is_active is False  




@pytest.mark.django_db
def test_non_admin_cannot_delete_user(api_client, funcionario_user, test_user):
    api_client.force_authenticate(user=funcionario_user)

    response = api_client.delete(f"/api/users/{test_user.id}/")

    assert response.status_code == 403
    assert User.objects.filter(id=test_user.id).exists()

@pytest.mark.django_db
def test_admin_can_access_users(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    response = api_client.get("/api/users/")
    assert response.status_code == 200

@pytest.mark.django_db
def test_non_admin_cannot_access_users(api_client, funcionario_user):
    api_client.force_authenticate(user=funcionario_user)
    response = api_client.get("/api/users/")
    assert response.status_code == 403

@pytest.mark.django_db
def test_usuario_get_serializer():
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass",
        system_role=2  
    )
    serializer = UsuarioGETSerializer(instance=user)
    assert serializer.data["system_role_description"] == "Funcionario"

@pytest.mark.django_db
@patch("src.apps.users.utils.tasks.send_welcome_email_task.apply_async")
@patch("src.apps.users.utils.tasks.update_system_role_task.apply_async")
def test_usuario_post_serializer(mock_update_role, mock_send_email):
    data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "securepassword",
        "system_role": 2
    }
    serializer = UsuarioPOSTSerializer(data=data)
    assert serializer.is_valid(), serializer.errors  
    user = serializer.save()

    assert user.username == "newuser"
    assert user.check_password("securepassword") is True  
    mock_send_email.assert_called_once()
    mock_update_role.assert_called_once()

@pytest.mark.django_db
def test_usuario_post_serializer_duplicate_email(user_factory):
    user_factory(username="existinguser", email="existing@example.com")

    data = {
        "username": "newuser",
        "email": "existing@example.com",
        "password": "securepassword",
        "system_role": 2
    }
    serializer = UsuarioPOSTSerializer(data=data)
    
    assert not serializer.is_valid()
    assert "email" in serializer.errors


def test_password_reset_request_serializer():
    data = {"email": "test@example.com"}
    serializer = PasswordResetRequestSerializer(data=data)
    assert serializer.is_valid()

@patch.object(UserService, "is_valid_reset_token", return_value=True)
def test_password_reset_serializer_valid(mock_token_validation):
    data = {
        "email": "test@example.com",
        "token": "123456",
        "new_password": "newsecurepassword"
    }
    serializer = PasswordResetSerializer(data=data)
    assert serializer.is_valid()

@patch.object(UserService, "is_valid_reset_token", return_value=False)
def test_password_reset_serializer_invalid_token(mock_token_validation):
    data = {
        "email": "test@example.com",
        "token": "wrongtoken",
        "new_password": "newsecurepassword"
    }
    serializer = PasswordResetSerializer(data=data)
    assert serializer.is_valid() is False
    assert "token" in serializer.errors

def test_password_reset_serializer_short_password():
    data = {
        "email": "test@example.com",
        "token": "123456",
        "new_password": "123"
    }
    serializer = PasswordResetSerializer(data=data)
    assert serializer.is_valid() is False
    assert "new_password" in serializer.errors