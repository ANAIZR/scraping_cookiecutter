import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.utils.services import WebScraperService, ScraperService, ScraperComparisonService

@pytest.mark.django_db
def test_get_expired_urls(mocker):
    mock_query = mocker.patch("src.apps.shared.models.scraperURL.ScraperURL.objects.filter")
    mock_exclude = mock_query.return_value.exclude
    mock_values_list = mock_exclude.return_value.values_list
    mock_values_list.return_value = ["https://example.com"]
    
    service = WebScraperService()
    result = service.get_expired_urls()
    
    assert result == ["https://example.com"]

@pytest.mark.django_db
def test_scraper_one_url_success(mocker):
    url = "https://example.com"
    with mocker.patch.dict("src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS", {1: MagicMock(return_value={"data": "Success"})}):
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
    with patch("src.apps.shared.services.MongoClient") as mock_mongo_client:
        mock_mongo_client.return_value.__getitem__.return_value["fs.files"].find.return_value = [{"_id": "123", "contenido": "test content", "source_url": url}]
        
        with patch.object(ScraperService, "process_document") as mock_process_document:
            service = ScraperService()
            service.extract_and_save_species(url)
            mock_process_document.assert_called()

@pytest.mark.django_db
def test_generate_comparison_report(mocker):
    url = "https://example.com"
    with patch("src.apps.shared.services.MongoClient") as mock_mongo_client:
        mock_mongo_client.return_value.__getitem__.return_value["collection"].find.return_value.sort.return_value = [{"_id": "1", "contenido": "old content"}, {"_id": "2", "contenido": "new content"}]
        
        with patch("src.apps.shared.services.ScraperComparisonService.generate_comparison") as mock_comparison_result:
            mock_comparison_result.return_value = {"has_changes": True, "info_agregada": ["url1"], "info_eliminada": []}
            
            with patch("src.apps.shared.services.ScraperComparisonService.save_or_update_comparison_to_postgres") as mock_save_comparison:
                service = ScraperComparisonService()
                result = service.get_comparison_for_url(url)
                
                assert result["status"] == "changed"
                mock_save_comparison.assert_called()
