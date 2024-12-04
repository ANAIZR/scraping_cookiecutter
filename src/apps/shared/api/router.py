from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter
from django.urls import path
from .viewsets.login_viewsets import LoginView
from .viewsets import pdf_viewsets, scraperURL_viewsets
from .viewsets.scraperFixture_viewsets import ScraperAPIView

router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register(r"urls", scraperURL_viewsets.ScraperURLViewSet, basename="urls")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("scraper-pdf/", pdf_viewsets.scrape_url, name="scraper_pdf"),
    path("scraper-get-pdf/", pdf_viewsets.get_scraped_url, name="get_scraper_pdf"),
    path("scraper-url/",  ScraperAPIView.as_view(), name="scraper_url"),
]
urlpatterns += router.urls
