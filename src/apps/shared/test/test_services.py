import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from src.apps.shared.utils.services import (
    WebScraperService,
    ScraperService,
    ScraperComparisonService,
)
from src.apps.shared.models.scraperURL import ScraperURL, Species, ReportComparison

@pytest.mark.django_db
def test_get_expired_urls(mocker):
    mock_query = mocker.patch("src.apps.shared.models.scraperURL.ScraperURL.objects.filter")
    mock_query.return_value.exclude.return_value.values_list.return_value = ["https://example.com"]
    service = WebScraperService()
    result = service.get_expired_urls()
    assert result == ["https://example.com"]

@pytest.mark.django_db
def test_scraper_one_url_success(mocker):
    url = "https://example.com"
    mock_scraper_function = mocker.patch("src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS.get")
    mock_scraper_function.return_value.return_value = {"data": "Success"}
    
    scraper_url = ScraperURL.objects.create(url=url, sobrenombre="test", estado_scrapeo="pendiente", mode_scrapeo=1)
    
    service = WebScraperService()
    result = service.scraper_one_url(url, "test")
    scraper_url.refresh_from_db()
    
    assert result == {"data": "Success"}
    assert scraper_url.estado_scrapeo == "exitoso"
    assert scraper_url.error_scrapeo == ""

@pytest.mark.django_db
def test_extract_and_save_species(mocker):
    url = "https://example.com"
    mock_mongo_client = mocker.patch("src.apps.shared.services.MongoClient")
    mock_mongo_client.return_value.__getitem__.return_value["fs.files"].find.return_value = [{"_id": "123", "contenido": "test content", "source_url": url}]
    mock_process_document = mocker.patch("src.apps.shared.services.ScraperService.process_document")
    
    service = ScraperService()
    service.extract_and_save_species(url)
    mock_process_document.assert_called()

@pytest.mark.django_db
def test_generate_comparison_report(mocker):
    url = "https://example.com"
    mock_mongo_client = mocker.patch("src.apps.shared.services.MongoClient")
    mock_mongo_client.return_value.__getitem__.return_value["collection"].find.return_value.sort.return_value = [{"_id": "1", "contenido": "old content"}, {"_id": "2", "contenido": "new content"}]
    mock_comparison_result = mocker.patch("src.apps.shared.services.ScraperComparisonService.generate_comparison")
    mock_comparison_result.return_value = {"has_changes": True, "info_agregada": ["url1"], "info_eliminada": []}
    mock_save_comparison = mocker.patch("src.apps.shared.services.ScraperComparisonService.save_or_update_comparison_to_postgres")
    
    service = ScraperComparisonService()
    result = service.get_comparison_for_url(url)
    
    assert result["status"] == "changed"
    mock_save_comparison.assert_called()
