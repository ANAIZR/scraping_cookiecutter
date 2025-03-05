import pytest
from unittest.mock import patch, MagicMock
from rest_framework.response import Response
from rest_framework.test import APIClient
from src.apps.users.models import User
from src.apps.shared.models.scraperURL import ScraperURL
from django.urls import reverse
from django.utils import timezone
import responses
from src.apps.shared.api.serializers import ScraperURLSerializer, SpeciesSerializer, ReportComparisonSerializer, SpeciesSubscriptionSerializer
from src.apps.shared.models import Species, ReportComparison, SpeciesSubscription
API_URL = reverse("scraper_url")

@pytest.mark.django_db
class TestScraperAPIView:

    def setup_method(self):
        self.client = APIClient()
        
        self.admin = User.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="adminpass"
        )
        self.admin.system_role = 1 
        self.admin.save()  

        self.scraper_url = ScraperURL.objects.create(
            url="https://example.com",
            sobrenombre="Test Scraper",
            type_file=1,
            time_choices=1,
            parameters={},
            mode_scrapeo=1,
        )


    @patch("src.apps.shared.utils.tasks.scraper_url_task.apply_async") 
    @patch("src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS", new_callable=dict) 
    def test_scraper_runs_successfully(self, mock_scraper_functions, mock_apply_async):
        self.client.force_authenticate(user=self.admin)

        mock_scraper_functions[1] = MagicMock(return_value=Response(
            {"data": "Scraper exitoso"}, status=200
        ))

        response = self.client.post(API_URL, {"url": "https://example.com"})

        mock_apply_async.assert_called_once_with(("https://example.com",))

        assert response.status_code == 202
        assert response.json() == {"status": "Tarea de scraping encolada exitosamente"}

    @patch("src.apps.shared.utils.tasks.scraper_url_task.apply_async")  
    def test_scraper_requires_authentication(self, mock_apply_async):
        response = self.client.post(API_URL, {"url": "https://example.com"})
        assert response.status_code == 401

    @patch("src.apps.shared.utils.tasks.scraper_url_task.apply_async") 
    def test_scraper_requires_admin_permissions(self, mock_apply_async):
        funcionario = User.objects.create_user(
            username="funcionario_user",
            email="funcionario@example.com",
            password="funcionariopass",
            system_role=2,
        )
        self.client.force_authenticate(user=funcionario)

        response = self.client.post(API_URL, {"url": "https://example.com"})
        assert response.status_code == 403

    @patch("src.apps.shared.utils.tasks.scraper_url_task.apply_async", side_effect=Exception("Error en Celery"))
    def test_scraper_function_raises_exception(self, mock_apply_async):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(API_URL, {"url": "https://example.com"})

        assert response.status_code == 500
        assert response.json() == {"error": "Error al encolar tarea: Error en Celery"}

    @patch("src.apps.shared.utils.tasks.scraper_url_task.apply_async")
    def test_scraper_fails_with_unknown_url(self, mock_apply_async):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(API_URL, {"url": "https://unknown.com"})

        assert response.status_code == 404
        assert response.json() == {"error": "No se encontraron parámetros para la URL: https://unknown.com"}

        mock_apply_async.assert_not_called()

    @patch("src.apps.shared.utils.tasks.scraper_url_task.apply_async")
    def test_scraper_updates_database(self, mock_apply_async):
        self.client.force_authenticate(user=self.admin)

        assert self.scraper_url.fecha_scraper is None

        response = self.client.post(API_URL, {"url": "https://example.com"})

        assert response.status_code == 202  
        assert response.json() == {"status": "Tarea de scraping encolada exitosamente"}

        self.scraper_url.fecha_scraper = timezone.now()
        self.scraper_url.save()
        self.scraper_url.refresh_from_db()

        assert self.scraper_url.fecha_scraper is not None

    @responses.activate
    def test_scraper_integration_with_external_source(self):
        self.client.force_authenticate(user=self.admin)

        if not ScraperURL.objects.filter(url="http://www.iucngisd.org/gisd/").exists():
            ScraperURL.objects.create(
                url="http://www.iucngisd.org/gisd/",
                sobrenombre="IUCNGISD",
                time_choices=3,
                mode_scrapeo=1
            )

        responses.add(
            responses.GET,
            "http://www.iucngisd.org/gisd/",
            body="<html><body><h1>External Page</h1></body></html>",
            status=200
        )

        response = self.client.post(API_URL, {"url": "http://www.iucngisd.org/gisd/"})

        assert response.status_code == 202
        assert response.json()["status"] == "Tarea de scraping encolada exitosamente"
    @pytest.mark.django_db
    def test_scraper_url_serializer_format_fecha_scraper():
        scraper = ScraperURL.objects.create(
            url="https://example.com",
            sobrenombre="Test Scraper",
            time_choices=1,
            fecha_scraper=None 
        )

        serializer = ScraperURLSerializer(instance=scraper)
        assert serializer.data["fecha_scraper"] == "Aún no se ha realizado el proceso de scraper"

    @pytest.mark.django_db
    def test_scraper_url_serializer_validation():
        ScraperURL.objects.create(url="https://example.com", sobrenombre="Test Scraper")
        
        data = {"url": "https://example.com", "sobrenombre": "Duplicate Test"}
        serializer = ScraperURLSerializer(data=data)

        assert not serializer.is_valid()
        assert "url" in serializer.errors  

    @pytest.mark.django_db
    def test_scraper_url_serializer_estado_fallido():
        scraper = ScraperURL.objects.create(
            url="https://example.com",
            sobrenombre="Test Scraper",
            time_choices=1,
            estado_scrapeo="fallido",
            error_scrapeo="Conexión rechazada"
        )

        serializer = ScraperURLSerializer(instance=scraper)
        assert serializer.data["error_scrapeo"] == "Conexión rechazada"

    @pytest.mark.django_db
    def test_species_serializer():
        scraper_source = ScraperURL.objects.create(url="https://example.com", sobrenombre="Test Scraper")
        species = Species.objects.create(scientific_name="Ficus elastica", scraper_source=scraper_source)

        serializer = SpeciesSerializer(instance=species)
        assert serializer.data["sobrenombre"] == "Test Scraper"

    @pytest.mark.django_db
    def test_report_comparison_serializer():
        scraper_source = ScraperURL.objects.create(url="https://example.com", sobrenombre="Test Scraper")
        report = ReportComparison.objects.create(scraper_source=scraper_source)

        serializer = ReportComparisonSerializer(instance=report)
        assert serializer.data["url"] == "https://example.com"

    @pytest.mark.django_db
    def test_species_subscription_serializer():
        subscription = SpeciesSubscription.objects.create(
            name_subscription="Test Subscription",
            scientific_name="Ficus elastica",
            distribution="South America",
            hosts="Insects"
        )

        serializer = SpeciesSubscriptionSerializer(instance=subscription)
        assert serializer.data["name_subscription"] == "Test Subscription"
        assert serializer.data["scientific_name"] == "Ficus elastica"
        assert "id" in serializer.data and "user" in serializer.data and "created_at" in serializer.data