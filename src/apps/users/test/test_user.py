import pytest
from rest_framework.test import APIClient
from src.apps.users.models import User

@pytest.mark.django_db
def test_admin_can_create_user():
    client = APIClient()
    admin = User.objects.create_user(
        username="admin_user",
        email="admin@example.com",
        password="adminpass",
        system_role=1
    )
    client.force_authenticate(user=admin)

    response = client.post("/api/users/", {
        "username": "newuser",
        "last_name": "UserLastName",  
        "email": "new@example.com",
        "password": "securepassword",
        "system_role": 2
    })

    assert response.status_code == 201  


@pytest.mark.django_db
def test_non_admin_cannot_create_user():
    client = APIClient()
    funcionario = User.objects.create_user(
        username="funcionario_user",
        email="funcionario@example.com",
        password="funcionariopass",
        system_role=2
    )
    client.force_authenticate(user=funcionario)

    response = client.post("/api/users/", {
        "username": "newuser",
        "email": "new@example.com",
        "password": "securepassword",
        "system_role": 2
    })
    
    assert response.status_code == 403  

@pytest.mark.django_db
def test_admin_can_update_user():
    client = APIClient()
    admin = User.objects.create_user(
        username="admin_user",
        email="admin@example.com",
        password="adminpass",
        system_role=1
    )
    user = User.objects.create_user(
        username="user_test",
        email="user@example.com",
        password="userpass",
        system_role=2
    )
    client.force_authenticate(user=admin)

    response = client.patch(f"/api/users/{user.id}/", {"username": "updated_user"})
    
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.username == "updated_user"

@pytest.mark.django_db
def test_non_admin_cannot_update_user():
    client = APIClient()
    funcionario = User.objects.create_user(
        username="funcionario_user",
        email="funcionario@example.com",
        password="funcionariopass",
        system_role=2
    )
    user = User.objects.create_user(
        username="user_test",
        email="user@example.com",
        password="userpass",
        system_role=2
    )
    client.force_authenticate(user=funcionario)

    response = client.patch(f"/api/users/{user.id}/", {"username": "updated_user"})
    
    assert response.status_code == 403  

@pytest.mark.django_db
def test_admin_can_delete_user():
    client = APIClient()
    admin = User.objects.create_user(
        username="admin_user",
        email="admin@example.com",
        password="adminpass",
        system_role=1
    )
    user = User.objects.create_user(
        username="user_test",
        email="user@example.com",
        password="userpass",
        system_role=2
    )
    client.force_authenticate(user=admin)

    response = client.delete(f"/api/users/{user.id}/")
    
    assert response.status_code == 204
    user.refresh_from_db()
    assert user.is_active is False 

@pytest.mark.django_db
def test_non_admin_cannot_delete_user():
    client = APIClient()
    funcionario = User.objects.create_user(
        username="funcionario_user",
        email="funcionario@example.com",
        password="funcionariopass",
        system_role=2
    )
    user = User.objects.create_user(
        username="user_test",
        email="user@example.com",
        password="userpass",
        system_role=2
    )
    client.force_authenticate(user=funcionario)

    response = client.delete(f"/api/users/{user.id}/")
    
    assert response.status_code == 403 
