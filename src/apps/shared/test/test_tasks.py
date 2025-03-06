import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.utils.tasks import scraper_url_task

@pytest.mark.django_db
@patch("src.apps.shared.utils.tasks.ScraperURL.objects.get")
@patch("src.apps.shared.utils.tasks.WebScraperService.scraper_one_url")
@patch("src.apps.shared.utils.tasks.process_scraped_data_task.apply_async")
@patch("src.apps.shared.utils.tasks.generate_comparison_report_task.apply_async")
def test_scraper_url_task_success(mock_generate_report, mock_process_data, mock_scraper_one_url, mock_scraper_get):
    mock_scraper_url = MagicMock()
    mock_scraper_url.sobrenombre = "Test Scraper"
    mock_scraper_url.estado_scrapeo = "pendiente"
    
    mock_scraper_get.return_value = mock_scraper_url
    mock_scraper_one_url.return_value = {"data": "Scraping successful"}

    result = scraper_url_task("self", "https://example.com")

    assert result["status"] == "exitoso"
    mock_process_data.assert_called_once()
    mock_generate_report.assert_called_once()
