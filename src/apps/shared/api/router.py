from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from django.urls import path

from .viewsets.login_viewsets import LoginView
from .viewsets import scraper_viewsets, urls_viewsets
router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r'urls', urls_viewsets.ScraperURLViewSet, basename='urls')

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path('scrape-url/', scraper_viewsets.scrape_url, name='scrape_url'),
    path('scraped-get-url/', scraper_viewsets.get_scraped_url, name='get_scraped_url'),
]
urlpatterns += router.urls
