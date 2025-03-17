import unittest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.scraper_service import WebScraperService
from src.apps.shared.models.urls import ScraperURL
from src.apps.shared.utils.scrapers import SCRAPER_FUNCTIONS, scraper_pdf
from django.utils import timezone
from django.test import TestCase

class TestWebScraperService(TestCase):
    
    def setUp(self):
        self.service = WebScraperService()
    
    @patch('src.apps.shared.services.scraper_service.ScraperURL.objects.filter')
    def test_get_expired_urls(self, mock_filter):
        # Arrange
        mock_filter.return_value.exclude.return_value.values_list.return_value = ["http://example.com"]
        
        # Act
        result = self.service.get_expired_urls()
        
        # Assert
        self.assertEqual(list(result), ["http://example.com"])
        mock_filter.assert_called()

    @patch('src.apps.shared.services.scraper_service.ScraperURL.objects.get')
    def test_scraper_one_url_not_found(self, mock_get):
        # Arrange
        mock_get.side_effect = ScraperURL.DoesNotExist
        
        # Act
        result = self.service.scraper_one_url("http://example.com", "test")
        
        # Assert
        self.assertIn("error", result)
        self.assertEqual(result["error"], "La URL http://example.com no se encuentra en la base de datos.")

    @patch('src.apps.shared.services.scraper_service.SCRAPER_FUNCTIONS', {"1": MagicMock(return_value={"data": "success"})})
    @patch('src.apps.shared.services.scraper_service.ScraperURL.objects.get')
    def test_scraper_one_url_successful(self, mock_get):
        # Arrange
        mock_scraper_url = MagicMock()
        mock_scraper_url.mode_scrapeo = "1"
        mock_get.return_value = mock_scraper_url
        
        # Act
        result = self.service.scraper_one_url("http://example.com", "test")
        
        # Assert
        self.assertEqual(result["data"], "success")

    @patch('src.apps.shared.services.scraper_service.scraper_pdf', return_value={"data": "pdf success"})
    @patch('src.apps.shared.services.scraper_service.ScraperURL.objects.get')
    def test_scraper_one_url_pdf(self, mock_get, mock_scraper_pdf):
        # Arrange
        mock_scraper_url = MagicMock()
        mock_scraper_url.mode_scrapeo = 7
        mock_scraper_url.parameters = {"start_page": 1, "end_page": 10}
        mock_get.return_value = mock_scraper_url
        
        # Act
        result = self.service.scraper_one_url("http://example.com", "test")
        
        # Assert
        self.assertEqual(result["data"], "pdf success")
        mock_scraper_pdf.assert_called_once()

    def test_integration_scraper_one_url(self):
        # Arrange
        scraper_url = ScraperURL.objects.create(url="http://example.com", mode_scrapeo="1", is_active=True)
        SCRAPER_FUNCTIONS["1"] = lambda url, sobrenombre: {"data": "integration success"}
        
        # Act
        result = self.service.scraper_one_url(scraper_url.url, "test")
        
        # Assert
        self.assertEqual(result["data"], "integration success")
