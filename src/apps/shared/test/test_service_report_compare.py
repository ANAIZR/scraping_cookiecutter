import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.report_compare import ScraperComparisonService

class TestScraperComparisonService:

    @pytest.fixture
    def mock_mongo_collection(self, mocker):
        mock_client = mocker.patch('src.apps.shared.services.report_compare.MongoClient')
        mock_db = mock_client.return_value.__getitem__.return_value
        mock_collection = mock_db.__getitem__.return_value
        return mock_collection

    @pytest.fixture
    def mock_report_comparison(self, mocker):
        return mocker.patch('src.apps.shared.models.ReportComparison.objects')

    @pytest.fixture
    def mock_scraper_url(self, mocker):
        return mocker.patch('src.apps.shared.models.ScraperURL.objects')

    def test_get_comparison_for_url_no_documents(self, mock_mongo_collection):
        mock_mongo_collection.find.return_value.sort.return_value = []
        service = ScraperComparisonService()
        result = service.get_comparison_for_url("https://example.com")

        assert result["status"] == "no_comparison"
        assert "Menos de dos registros encontrados." in result["message"]

    def test_get_comparison_for_url_existing_report(self, mock_mongo_collection, mock_report_comparison):
        mock_mongo_collection.find.return_value.sort.return_value = [
            {"_id": "1", "contenido": "content1"},
            {"_id": "2", "contenido": "content2"},
        ]
        mock_report_comparison.filter.return_value.first.return_value = MagicMock(object_id1="1", object_id2="2")

        service = ScraperComparisonService()
        result = service.get_comparison_for_url("https://example.com")

        assert result["status"] == "duplicate"
        assert "La comparación ya fue realizada anteriormente." in result["message"]

    def test_compare_and_save_no_changes(self, mock_mongo_collection):
        service = ScraperComparisonService()
        mock_mongo_collection.find.return_value.sort.return_value = [
            {"_id": "1", "contenido": "same content"},
            {"_id": "2", "contenido": "same content"},
        ]
        result = service.get_comparison_for_url("https://example.com")

        assert result["status"] == "no_changes"
        assert "No se detectaron cambios en la comparación." in result["message"]

    def test_compare_and_save_with_changes(self, mock_mongo_collection, mock_report_comparison, mock_scraper_url):
        service = ScraperComparisonService()
        mock_mongo_collection.find.return_value.sort.return_value = [
            {"_id": "1", "contenido": "old link1\nold link2"},
            {"_id": "2", "contenido": "old link1\nnew link3"},
        ]
        mock_scraper_url.get_or_create.return_value = (MagicMock(), True)

        result = service.get_comparison_for_url("https://example.com")

        assert result["status"] == "changed"
        assert "Se detectaron cambios en la comparación." in result["message"]
