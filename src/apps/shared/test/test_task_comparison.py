import unittest
from unittest.mock import patch, MagicMock
from src.apps.shared.tasks.comparison_tasks import generate_comparison_report_task

class TestGenerateComparisonReportTask(unittest.TestCase):
    
    @patch('src.apps.shared.tasks.comparison_tasks.ScraperComparisonService')
    def test_generate_comparison_report_task_no_url(self, mock_service):
        # Act
        result = generate_comparison_report_task("")
        
        # Assert
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "URL inválida")
        mock_service.assert_not_called()
    
    @patch('src.apps.shared.tasks.comparison_tasks.ScraperComparisonService')
    def test_generate_comparison_report_task_no_comparison(self, mock_service):
        # Arrange
        mock_instance = mock_service.return_value
        mock_instance.get_comparison_for_url.return_value = {"status": "no_comparison"}
        
        # Act
        result = generate_comparison_report_task("http://example.com")
        
        # Assert
        self.assertEqual(result["status"], "no_comparison")
        mock_instance.get_comparison_for_url.assert_called_once_with("http://example.com")
    
    @patch('src.apps.shared.tasks.comparison_tasks.ScraperComparisonService')
    def test_generate_comparison_report_task_changed(self, mock_service):
        # Arrange
        mock_instance = mock_service.return_value
        mock_instance.get_comparison_for_url.return_value = {
            "status": "changed",
            "info_agregada": ["http://new-url.com"],
            "info_eliminada": ["http://old-url.com"],
            "estructura_cambio": True
        }
        
        # Act
        result = generate_comparison_report_task("http://example.com")
        
        # Assert
        self.assertEqual(result["status"], "changed")
        self.assertIn("http://new-url.com", result["info_agregada"])
        self.assertIn("http://old-url.com", result["info_eliminada"])
        self.assertTrue(result["estructura_cambio"])
        mock_instance.get_comparison_for_url.assert_called_once_with("http://example.com")
    
    @patch('src.apps.shared.tasks.comparison_tasks.ScraperComparisonService')
    def test_generate_comparison_report_task_exception(self, mock_service):
        # Arrange
        mock_instance = mock_service.return_value
        mock_instance.get_comparison_for_url.side_effect = Exception("Unexpected Error")
        
        # Act
        result = generate_comparison_report_task("http://example.com")
        
        # Assert
        self.assertEqual(result["status"], "error")
        self.assertIn("Error interno", result["message"])
        mock_instance.get_comparison_for_url.assert_called_once_with("http://example.com")

