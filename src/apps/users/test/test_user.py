import pytest
from rest_framework.test import APIClient
from src.apps.users.models import User

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin_user",
        email="admin@example.com",
        password="adminpass",
        system_role=1
    )

@pytest.fixture
def funcionario_user(db):
    return User.objects.create_user(
        username="funcionario_user",
        email="funcionario@example.com",
        password="funcionariopass",
        system_role=2
    )

@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username="user_test",
        email="user@example.com",
        password="userpass",
        system_role=2
    )

@pytest.mark.django_db
def test_admin_can_create_user(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.post("/api/users/", {
        "username": "newuser",
        "last_name": "UserLastName",
        "email": "new@example.com",
        "password": "securepassword",
        "system_role": 2
    })

    assert response.status_code == 201
    assert User.objects.filter(username="newuser").exists()


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


@pytest.mark.django_db
def test_admin_can_delete_user(api_client, admin_user, test_user):
    api_client.force_authenticate(user=admin_user)

    response = api_client.delete(f"/api/users/{test_user.id}/")

    assert response.status_code == 204

    with pytest.raises(User.DoesNotExist):
        User.objects.get(id=test_user.id)


@pytest.mark.django_db
def test_non_admin_cannot_delete_user(api_client, funcionario_user, test_user):
    api_client.force_authenticate(user=funcionario_user)

    response = api_client.delete(f"/api/users/{test_user.id}/")

    assert response.status_code == 403

    assert User.objects.filter(id=test_user.id).exists()
