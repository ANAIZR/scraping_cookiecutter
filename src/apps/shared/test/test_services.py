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
    result = list(service.get_expired_urls()) 
    
    assert result == ["https://example.com"]

@pytest.mark.django_db
def test_scraper_one_url_success(mocker):
    url = "https://example.com"
    
    with patch.dict("src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS", {1: MagicMock(return_value={"data": "Success"})}):
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
    
    mock_collection = MagicMock()
    mock_collection.find.return_value = [{"_id": "123", "contenido": "test content", "source_url": url}]
    
    with patch.object(ScraperService, "process_document") as mock_process_document, \
         patch("src.apps.shared.utils.services.ThreadPoolExecutor") as mock_executor:
        
        service = ScraperService()
        service.collection = mock_collection  
        mock_executor.return_value.__enter__.return_value.submit.side_effect = lambda func, doc: func(doc)

        service.extract_and_save_species(url)

        mock_process_document.assert_called()



@pytest.mark.django_db
def test_generate_comparison_report(mocker):
    url = "https://example.com"
    with patch("src.apps.shared.utils.services.ScraperComparisonService.generate_comparison") as mock_comparison_result:
        mock_comparison_result.return_value = {"has_changes": True, "info_agregada": ["url1"], "info_eliminada": []}
        
        with patch("src.apps.shared.utils.services.ScraperComparisonService.save_or_update_comparison_to_postgres") as mock_save_comparison:
            service = ScraperComparisonService()
            result = service.get_comparison_for_url(url)
            
            assert result["status"] == "changed"
            mock_save_comparison.assert_called()
