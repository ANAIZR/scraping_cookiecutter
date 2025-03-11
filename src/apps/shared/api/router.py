from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from django.urls import path
from .viewsets.login_viewsets import LoginView
from .viewsets import get_viewset_scraper
from .viewsets.scraperFixture_viewsets import ScraperAPIView, ScraperURLCABIView
from .viewsets.scraperURL_viewsets import (
    SpeciesViewSet,
    SpeciesCABIViewSet,
    ReportComparisonDetailView,
    SpeciesSubscriptionViewSet,
    ScraperURLViewSet,
    get_related_species
)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from urllib.parse import unquote


router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r"urls", ScraperURLViewSet, basename="urls")
router.register(r"species", SpeciesViewSet, basename="especies")
router.register(r"species-cabi", SpeciesCABIViewSet, basename="especies_cabi")

router.register(
    r"subscription", SpeciesSubscriptionViewSet, basename="subscription"
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path(
        "scraper-get-url/", get_viewset_scraper.get_scraper_url, name="get_scraper_url"
    ),
    path("scraper-url/", ScraperAPIView.as_view(), name="scraper_url"),
    path("scraper-url-cabi/", ScraperURLCABIView.as_view(), name="scraper_url_cabi"),

    path(
        "report-comparison/<int:scraper_id>/",
        ReportComparisonDetailView.as_view(),
        name="report-comparison-detail",
    ),
    path("related_species/<str:query>/", get_related_species, name="related_species"),


]
urlpatterns += router.urls



