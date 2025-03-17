import unittest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.report_compare_service import ScraperComparisonService
from src.apps.shared.models.species import ReportComparison
from src.apps.shared.models.urls import ScraperURL
from pymongo import MongoClient
from django.conf import settings
from django.test import TestCase

class TestScraperComparisonService(TestCase):
    
    def setUp(self):
        self.service = ScraperComparisonService()
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["collection"]

    @patch('src.apps.shared.services.report_compare_service.MongoClient')
    def test_get_comparison_for_url_no_documents(self, mock_mongo_client):
        # Arrange
        self.collection.find.return_value.sort.return_value = []
        
        # Act
        result = self.service.get_comparison_for_url("http://example.com")
        
        # Assert
        self.assertEqual(result["status"], "no_comparison")
        self.assertEqual(result["message"], "Menos de dos registros encontrados.")

    @patch('src.apps.shared.services.report_compare_service.ReportComparison.objects.filter')
    def test_get_comparison_for_url_existing_report(self, mock_report_filter):
        # Arrange
        mock_report = MagicMock()
        mock_report.object_id1 = "id1"
        mock_report.object_id2 = "id2"
        mock_report_filter.return_value.first.return_value = mock_report
        
        self.collection.find.return_value.sort.return_value = [{"_id": "id1"}, {"_id": "id2"}]
        
        # Act
        result = self.service.get_comparison_for_url("http://example.com")
        
        # Assert
        self.assertEqual(result["status"], "duplicate")

    def test_generate_comparison_detects_changes(self):
        # Arrange
        content1 = "Enlaces scrapeados:\nhttp://old.com\nEnlaces no procesados:"
        content2 = "Enlaces scrapeados:\nhttp://new.com\nEnlaces no procesados:"
        
        # Act
        result = self.service.generate_comparison(content1, content2)
        
        # Assert
        self.assertTrue(result["estructura_cambio"])
        self.assertIn("http://new.com", result["info_agregada"])
        self.assertIn("http://old.com", result["info_eliminada"])

    @patch('src.apps.shared.services.report_compare_service.ReportComparison.objects.update_or_create')
    @patch('src.apps.shared.services.report_compare_service.ScraperURL.objects.get_or_create')
    def test_save_or_update_comparison_to_postgres(self, mock_get_or_create, mock_update_or_create):
        # Arrange
        url = "http://example.com"
        object_id1 = "id1"
        object_id2 = "id2"
        comparison_result = {"info_agregada": ["new_info"], "info_eliminada": ["old_info"], "estructura_cambio": True}
        
        # Act
        self.service.save_or_update_comparison_to_postgres(url, object_id1, object_id2, comparison_result)
        
        # Assert
        mock_get_or_create.assert_called_once_with(url=url)
        mock_update_or_create.assert_called()

    def test_full_integration_comparison(self):
        # Arrange
        url = "http://example.com"
        doc1 = {"_id": "id1", "contenido": "Enlaces scrapeados:\nhttp://old.com\nEnlaces no procesados:"}
        doc2 = {"_id": "id2", "contenido": "Enlaces scrapeados:\nhttp://new.com\nEnlaces no procesados:"}
        
        self.collection.find.return_value.sort.return_value = [doc1, doc2]
        
        # Act
        result = self.service.get_comparison_for_url(url)
        
        # Assert
        self.assertEqual(result["status"], "changed")
        self.assertEqual(result["message"], "Se detectaron cambios en la comparación.")
