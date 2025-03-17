import unittest
import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.tasks.scraper_tasks import (
    process_scraped_data_task,
    scraper_url_task,
    scraper_expired_urls_task,
)

class TestScraperTasks(unittest.TestCase):
    
    @patch('src.apps.shared.tasks.scraper_tasks.OllamaService')
    def test_process_scraped_data_task_with_url(self, mock_service):
        # Arrange
        mock_instance = mock_service.return_value
        
        # Act
        result = process_scraped_data_task("http://example.com")
        
        # Assert
        mock_instance.extract_and_save_species.assert_called_once_with("http://example.com")
        self.assertEqual(result, "http://example.com")
    @pytest.mark.django_db
    @patch('src.apps.shared.tasks.scraper_tasks.WebScraperService')
    @patch('src.apps.shared.tasks.scraper_tasks.ScraperURL.objects.get')
    def test_scraper_url_task_successful(self, mock_get, mock_service):
        # Arrange
        mock_scraper_url = MagicMock()
        mock_scraper_url.estado_scrapeo = "pendiente"
        mock_get.return_value = mock_scraper_url
        mock_instance = mock_service.return_value
        mock_instance.scraper_one_url.return_value = {"data": "scraped_data"}
        
        # Act
        result = scraper_url_task("http://example.com")
        
        # Assert
        self.assertEqual(result["status"], "exitoso")
        self.assertEqual(result["data"], "scraped_data")
    
    @patch('src.apps.shared.tasks.scraper_tasks.WebScraperService')
    @patch('src.apps.shared.tasks.scraper_tasks.chain')
    def test_scraper_expired_urls_task(self, mock_chain, mock_service):
        # Arrange
        mock_instance = mock_service.return_value
        mock_instance.get_expired_urls.return_value = ["http://example1.com", "http://example2.com"]
        
        # Act
        scraper_expired_urls_task()
        
        # Assert
        mock_instance.get_expired_urls.assert_called_once()
        mock_chain.assert_called()

