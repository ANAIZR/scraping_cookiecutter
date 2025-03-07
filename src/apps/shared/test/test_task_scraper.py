import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.tasks.scraper_tasks import (
    scraper_url_task, process_scraped_data_task, scraper_expired_urls_task
)

class TestScraperTasks:

    @pytest.fixture
    def mock_scraper_service(self, mocker):
        return mocker.patch('src.apps.shared.services.scraper.WebScraperService')

    @pytest.fixture
    def mock_ollama_service(self, mocker):
        return mocker.patch('src.apps.shared.services.ollama.OllamaService')

    @pytest.fixture
    def mock_scraper_url_model(self, mocker):
        return mocker.patch('src.apps.shared.models.scraperURL.ScraperURL.objects')

    def test_process_scraped_data_task(self, mock_ollama_service):
        mock_instance = mock_ollama_service.return_value
        mock_instance.extract_and_save_species.return_value = None

        result = process_scraped_data_task(None, "https://example.com")
        assert result == "https://example.com"
        mock_instance.extract_and_save_species.assert_called_once_with("https://example.com")

    def test_scraper_url_task_not_found(self, mock_scraper_url_model):
        mock_scraper_url_model.get.side_effect = mock_scraper_url_model.model.DoesNotExist
        result = scraper_url_task(None, "https://notfound.com")

        assert result["status"] == "failed"
        assert "ScraperURL no encontrado" in result["error"]

    def test_scraper_url_task_success(self, mock_scraper_service, mock_scraper_url_model):
        mock_scraper_url = MagicMock(sobrenombre="test", estado_scrapeo="pendiente")
        mock_scraper_url_model.get.return_value = mock_scraper_url
        mock_scraper_service.return_value.scraper_one_url.return_value = {"data": "scraped"}

        result = scraper_url_task(None, "https://validsite.com")
        assert result["status"] == "exitoso"
        assert "data" in result["data"]

    def test_scraper_expired_urls_task_no_urls(self, mock_scraper_service):
        mock_scraper_service.return_value.get_expired_urls.return_value = []
        result = scraper_expired_urls_task(None)

        assert result is None
        mock_scraper_service.return_value.get_expired_urls.assert_called_once()
