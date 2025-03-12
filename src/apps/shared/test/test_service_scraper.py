import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.scraper_service import WebScraperService
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

class TestWebScraperService:

    @pytest.fixture
    def mock_scraper_url(self, mocker):
        return mocker.patch('src.apps.shared.models.ScraperURL.objects')

    @pytest.fixture
    def mock_scraper_functions(self, mocker):
        return mocker.patch('src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS')

    @pytest.fixture
    def mock_scraper_pdf(self, mocker):
        return mocker.patch('src.apps.shared.utils.scrapers.scraper_pdf')

    def test_get_expired_urls(self, mock_scraper_url):
        mock_queryset = MagicMock()
        mock_queryset.__iter__.return_value = ["https://expired.com"]  
        mock_scraper_url.filter.return_value.exclude.return_value.values_list.return_value = mock_queryset

        service = WebScraperService()
        urls = service.get_expired_urls()

        print(f"Resultado de get_expired_urls(): {urls}")  # Depuración

        assert urls == ["https://expired.com"]



    def test_scraper_one_url_not_found(self, mock_scraper_url):
        mock_scraper_url.get.side_effect = ObjectDoesNotExist  

        service = WebScraperService()
        result = service.scraper_one_url("https://notfound.com", "test")

        print(f"Mensaje de error recibido: {result['error']}") 

        assert "error" in result
        assert "no se encuentra en la base de datos" in result["error"]  


    def test_scraper_one_url_invalid_mode(self, mock_scraper_url, mock_scraper_functions):
        mock_instance = MagicMock(mode_scrapeo=99)
        mock_scraper_url.get.return_value = mock_instance
        mock_scraper_functions.get.return_value = None
        service = WebScraperService()
        result = service.scraper_one_url("https://invalidmode.com", "test")

        assert "error" in result
        assert "no registrado en SCRAPER_FUNCTIONS" in result["error"]

    def test_scraper_one_url_pdf(self, mock_scraper_url, mock_scraper_pdf):
        mock_instance = MagicMock(mode_scrapeo=7, parameters={"start_page": 1, "end_page": 5})
        mock_scraper_url.get.return_value = mock_instance
        mock_scraper_pdf.side_effect = lambda url, params: {"success": True} 

        service = WebScraperService()
        result = service.scraper_one_url("https://pdfsite.com", "test")

        print(f"Resultado recibido: {result}") 

        assert result == {"success": True}

    def test_scraper_one_url_generic_scraper(self, mock_scraper_url, mock_scraper_functions):
        mock_instance = MagicMock()
        mock_instance.mode_scrapeo = 1  
        mock_scraper_url.get.return_value = mock_instance

        mock_scraper_functions.get.return_value = lambda url: {"data": "scraped"} 

        service = WebScraperService()
        result = service.scraper_one_url("https://validsite.com", "test")

        print(f"Resultado recibido: {result}")  # 🔍 Depuración

        assert "data" in result
        assert result["data"] == "scraped"
