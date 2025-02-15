from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from django.urls import path
from .viewsets.login_viewsets import LoginView
from .viewsets import get_viewset_scraper, scraperURL_viewsets
from .viewsets.scraperFixture_viewsets import ScraperAPIView
router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r"urls", scraperURL_viewsets.ScraperURLViewSet, basename="urls")
router.register(r"species", scraperURL_viewsets.SpeciesURLViewSet, basename="especies")
urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("scraper-get-url/", get_viewset_scraper.get_scraper_url, name="get_scraper_url"),
    path("scraper-url/",  ScraperAPIView.as_view(), name="scraper_url"),
]
urlpatterns += router.urls
