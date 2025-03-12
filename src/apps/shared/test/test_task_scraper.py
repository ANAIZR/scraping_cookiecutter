import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.tasks.scraper_tasks import (
    scraper_url_task, process_scraped_data_task, scraper_expired_urls_task
)
import logging

logger = logging.getLogger(__name__)
class TestScraperTasks:

    @pytest.fixture
    def mock_scraper_service(self, mocker):
        return mocker.patch('src.apps.shared.services.scraper_service.WebScraperService')

    @pytest.fixture
    def mock_ollama_service(self, mocker):
        return mocker.patch('src.apps.shared.services.ollama.OllamaService')

    @pytest.fixture
    def mock_scraper_url_model(self, mocker):
        return mocker.patch('src.apps.shared.models.ScraperURL.objects')

    from unittest.mock import patch

    @patch("src.apps.shared.tasks.scraper_tasks.OllamaService")
    def test_process_scraped_data_task(self,mock_ollama_service):
        mock_instance = mock_ollama_service.return_value
        mock_instance.extract_and_save_species.return_value = None

        result = process_scraped_data_task.apply(args=["https://example.com"]).result 

        assert result == "https://example.com"




    @patch("src.apps.shared.tasks.scraper_tasks.ScraperURL")
    def test_scraper_url_task_not_found(self, mock_scraper_url_model):
        mock_scraper_url_model.objects.filter.return_value.exists.return_value = False
        mock_scraper_url_model.objects.get.side_effect = Exception("ScraperURL no encontrado")

        result = scraper_url_task(None, "https://notfound.com")

        print(f"Resultado de scraper_url_task: {result}")  
        assert result["status"] == "failed"
        assert "ScraperURL no encontrado" in result["error"]






    @patch("src.apps.shared.tasks.scraper_tasks.WebScraperService") 
    @patch("src.apps.shared.tasks.scraper_tasks.ScraperURL") 
    def test_scraper_url_task_success(self,mock_scraper_url_model, mock_scraper_service): 
        mock_scraper_url_model.objects.filter.return_value.exists.return_value = False

        mock_scraper_url = MagicMock(sobrenombre="test", estado_scrapeo="pendiente")
        mock_scraper_url_model.objects.get.return_value = mock_scraper_url

        mock_scraper_service.return_value.scraper_one_url.return_value = {"data": "scraped"}

        result = scraper_url_task(None, "https://validsite.com")

        assert result["status"] == "exitoso"
        assert "data" in result["data"]
        assert result["data"] == {"data": "scraped"}

        assert mock_scraper_url.estado_scrapeo == "exitoso"

        mock_scraper_url.save.assert_called()


    @patch("src.apps.shared.tasks.scraper_tasks.WebScraperService")
    def test_scraper_expired_urls_task_no_urls(self,mock_scraper_service):
        mock_scraper_service.return_value.get_expired_urls.return_value = []

        result = scraper_expired_urls_task.apply(args=[None])  

        assert result is None or result.result is None  
        mock_scraper_service.return_value.get_expired_urls.assert_called_once()
        logger.info("✅ Test completado correctamente sin URLs expiradas.")