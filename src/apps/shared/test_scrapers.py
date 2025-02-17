import pytest
from unittest.mock import patch, MagicMock
from rest_framework.response import Response
from rest_framework.test import APIClient
from src.apps.users.models import User
from src.apps.shared.models.scraperURL import ScraperURL

API_URL = "http://127.0.0.1:8000/api/v1/scraper-url/"


@pytest.mark.django_db
class TestScraperAPIView:

    def setup_method(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="adminpass",
            system_role=1,
        )
        self.scraper_url = ScraperURL.objects.create(
            url="https://example.com",
            sobrenombre="Test Scraper",
            type_file=1,
            time_choices=1,
            parameters={},
            mode_scrapeo=1,
        )

    @patch(
        "src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS",
        new_callable=dict,
    )
    def test_scraper_runs_successfully(self, mock_scraper_functions):
        self.client.force_authenticate(user=self.admin)

        mock_scraper_functions[1] = lambda **kwargs: Response(
            {"data": "Scraper exitoso"}, status=200
        )

        response = self.client.post(API_URL, {"url": "https://example.com"})

        assert response.status_code == 200
        assert response.json() == {"data": "Scraper exitoso"}

    def test_scraper_requires_authentication(self):
        response = self.client.post(API_URL, {"url": "https://example.com"})

        assert response.status_code == 401

    def test_scraper_requires_admin_permissions(self):
        funcionario = User.objects.create_user(
            username="funcionario_user",
            email="funcionario@example.com",
            password="funcionariopass",
            system_role=2,
        )
        self.client.force_authenticate(user=funcionario)

        response = self.client.post(API_URL, {"url": "https://example.com"})

        assert response.status_code == 403

    @patch("src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS", new_callable=dict)
    def test_scraper_function_raises_exception(self, mock_scraper_functions):
        self.client.force_authenticate(user=self.admin)

        def mock_scraper_function(**kwargs):
            raise ValueError("Error en el scraper")
        
        mock_scraper_functions[1] = mock_scraper_function

        response = self.client.post(API_URL, {"url": "https://example.com"})

        assert response.status_code == 500
        assert response.json() == {"error": "Error durante el scrapeo: Error en el scraper"}


    def test_scraper_fails_with_unknown_url(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(API_URL, {"url": "https://unknown.com"})

        assert response.status_code == 404
        assert response.json() == {"error": "No se encontraron parámetros para la URL: https://unknown.com"}


    @patch("src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS", new_callable=dict)
    def test_scraper_updates_database(self, mock_scraper_functions):
        self.client.force_authenticate(user=self.admin)

        def mock_scraper_function(**kwargs):
            return Response({"data": "Scraper exitoso"}, status=200)

        mock_scraper_functions[1] = mock_scraper_function

        response = self.client.post(API_URL, {"url": "https://example.com"})
        assert response.status_code == 200

        self.scraper_url.refresh_from_db()
        assert self.scraper_url.fecha_scraper is not None
