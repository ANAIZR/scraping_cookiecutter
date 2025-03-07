from rest_framework.test import APITestCase
from src.apps.users.models import User
from src.apps.shared.models.scraperURL import ScraperURL, Species, ReportComparison, SpeciesSubscription
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock
import responses
from rest_framework.response import Response
from src.apps.shared.api.serializers.scraperURL_serializers import ScraperURLSerializer, SpeciesSerializer, ReportComparisonSerializer, SpeciesSubscriptionSerializer


class TestScraperAPIView(APITestCase):

    def setUp(self): 
        self.client = self.client  

        self.admin = User.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="adminpass"
        )
        self.admin.system_role = 1  
        self.admin.save()

        self.client.force_authenticate(user=self.admin)

        self.scraper_url = ScraperURL.objects.create(
            url="https://example.com",
            sobrenombre="Test Scraper",
            type_file=1,
            time_choices=1,
            parameters={},
            mode_scrapeo=1,
        )

    @patch("src.apps.shared.tasks.scraper_tasks.scraper_url_task.apply_async") 
    @patch("src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS", new_callable=dict) 
    def test_scraper_runs_successfully(self, mock_scraper_functions, mock_apply_async):
        mock_scraper_functions[1] = MagicMock(return_value=Response(
            {"data": "Scraper exitoso"}, status=200
        ))

        response = self.client.post(reverse("scraper_url"), {"url": "https://example.com"})

        mock_apply_async.assert_called_once_with(("https://example.com",))

        assert response.status_code == 202
        assert response.json() == {"status": "Tarea de scraping encolada exitosamente"}

    def test_scraper_requires_authentication(self):
        self.client.logout()
        response = self.client.post(reverse("scraper_url"), {"url": "https://example.com"})
        assert response.status_code == 401

    def test_scraper_requires_admin_permissions(self):
        funcionario = User.objects.create_user(
            username="funcionario_user",
            email="funcionario@example.com",
            password="funcionariopass",
            system_role=2,
        )
        self.client.force_authenticate(user=funcionario)

        response = self.client.post(reverse("scraper_url"), {"url": "https://example.com"})
        assert response.status_code == 403

    @patch("src.apps.shared.tasks.scraper_tasks.scraper_url_task.apply_async", side_effect=Exception("Error en Celery"))
    def test_scraper_function_raises_exception(self, mock_apply_async):
        response = self.client.post(reverse("scraper_url"), {"url": "https://example.com"})

        assert response.status_code == 500
        assert response.json() == {"error": "Error al encolar tarea: Error en Celery"}

    def test_scraper_fails_with_unknown_url(self):
        response = self.client.post(reverse("scraper_url"), {"url": "https://unknown.com"})

        assert response.status_code == 404
        assert response.json() == {"error": "No se encontraron parámetros para la URL: https://unknown.com"}

    def test_scraper_updates_database(self):
        assert self.scraper_url.fecha_scraper is None

        response = self.client.post(reverse("scraper_url"), {"url": "https://example.com"})

        assert response.status_code == 202  
        assert response.json() == {"status": "Tarea de scraping encolada exitosamente"}

        self.scraper_url.fecha_scraper = timezone.now()
        self.scraper_url.save()
        self.scraper_url.refresh_from_db()

        assert self.scraper_url.fecha_scraper is not None

    def test_scraper_url_serializer_format_fecha_scraper(self):
        scraper = ScraperURL.objects.create(
            url="https://example.com",
            sobrenombre="Test Scraper",
            time_choices=1,
            fecha_scraper=None 
        )

        serializer = ScraperURLSerializer(instance=scraper)
        assert serializer.data["fecha_scraper"] == "Aún no se ha realizado el proceso de scraper"

    def test_scraper_url_serializer_validation(self):
        ScraperURL.objects.create(url="https://example.com", sobrenombre="Test Scraper")
        
        data = {"url": "https://example.com", "sobrenombre": "Duplicate Test"}
        serializer = ScraperURLSerializer(data=data)

        assert not serializer.is_valid()
        assert "url" in serializer.errors  

    def test_scraper_url_list(self):
        ScraperURL.objects.create(url="https://example.com", sobrenombre="Test Scraper")

        response = self.client.get(reverse("urls-list"))
        assert response.status_code == 200
        assert len(response.data["results"]) > 0

    def test_species_list(self):
        response = self.client.get(reverse("species-list"))
        assert response.status_code == 200

    def test_report_comparison_not_found(self):
        response = self.client.get(reverse("report-comparison-detail", kwargs={"scraper_id": 9999}))
        assert response.status_code == 404

    def test_species_subscription_create(self):
        data = {
            "name_subscription": "Test Subscription",
            "scientific_name": "Test Plant"
        }

        response = self.client.post(reverse("subscription-list"), data)
        assert response.status_code == 201
