from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from django.urls import path
from .viewsets.scraperFixture_viewsets import ScraperAPIView
from .viewsets.species_viewsets import (
    SpeciesViewSet,
    ReportComparisonDetailView,
    SpeciesSubscriptionViewSet,
    ScraperURLViewSet,
    SpeciesCABIViewSet,
    get_related_species,
    get_plague_summary_view,
    get_plague_news
)

router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r"urls", ScraperURLViewSet, basename="urls")
router.register(r"species", SpeciesViewSet, basename="species")
router.register(r"species-cabi", SpeciesCABIViewSet, basename="species_cabi")

router.register(
    r"subscription", SpeciesSubscriptionViewSet, basename="subscription"
)

urlpatterns = [
    path("scraper-url/", ScraperAPIView.as_view(), name="scraper_url"),
    path(
        "report-comparison/<int:scraper_id>/",
        ReportComparisonDetailView.as_view(),
        name="report-comparison-detail",
    ),
    path("related_species/<str:query>/", get_related_species, name="related_species"),
        
    path('plague-summary/<int:cabi_id>/', get_plague_summary_view, name='plague_summary'),
    path('api/plague-news/<int:cabi_id>/', get_plague_news, name='plague-news'),


]
urlpatterns += router.urls
