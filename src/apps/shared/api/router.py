from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from django.urls import path

from .viewsets.login_viewsets import LoginView

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
]
urlpatterns += router.urls
