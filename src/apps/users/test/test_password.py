from unittest.mock import patch
from src.apps.users.api.serializers import PasswordResetRequestSerializer, PasswordResetSerializer
from src.apps.users.utils.services import UserService
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
