from django.urls import path, include
from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from src.apps.users.api.views import UsuarioView, PasswordResetRequestView, PasswordResetView, LoginView

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UsuarioView, basename="users")

additional_urlpatterns = [
    path('users/password-reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('users/password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('login/', LoginView.as_view(), name='login'),
]

urlpatterns = additional_urlpatterns + router.urls

app_name = "api"
