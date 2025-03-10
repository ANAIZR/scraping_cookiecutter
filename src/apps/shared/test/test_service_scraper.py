import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.scraper import WebScraperService
from django.utils import timezone

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
        mock_scraper_url.filter.return_value.exclude.return_value.values_list.return_value = ["https://expired.com"]
        service = WebScraperService()
        urls = service.get_expired_urls()
        
        assert urls == ["https://expired.com"]

    def test_scraper_one_url_not_found(self, mock_scraper_url):
        mock_scraper_url.get.side_effect = mock_scraper_url.model.DoesNotExist
        service = WebScraperService()
        result = service.scraper_one_url("https://notfound.com", "test")

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
        mock_scraper_pdf.return_value = {"success": True}
        
        service = WebScraperService()
        result = service.scraper_one_url("https://pdfsite.com", "test")

        assert result == {"success": True}

    def test_scraper_one_url_generic_scraper(self, mock_scraper_url, mock_scraper_functions):
        mock_instance = MagicMock(mode_scrapeo=1)
        mock_scraper_url.get.return_value = mock_instance
        mock_scraper_function = MagicMock(return_value={"data": "scraped"})
        mock_scraper_functions.get.return_value = mock_scraper_function

        service = WebScraperService()
        result = service.scraper_one_url("https://validsite.com", "test")

        assert "data" in result
        assert result["data"] == "scraped"