import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.tasks.comparison_tasks import generate_comparison_report_task

class TestGenerateComparisonReportTask:

    @pytest.fixture
    def mock_comparison_service(self, mocker):
        return mocker.patch('src.apps.shared.services.report_compare.ScraperComparisonService')

    def test_generate_comparison_report_task_invalid_url(self):
        result = generate_comparison_report_task(None, None)
        assert result["status"] == "error"
        assert result["message"] == "URL inválida"

    def test_generate_comparison_report_task_no_comparison(self, mock_comparison_service):
        mock_comparison_service.return_value.get_comparison_for_url.return_value = {"status": "no_comparison"}
        result = generate_comparison_report_task(None, "https://example.com")
        assert result["status"] == "no_comparison"

    def test_generate_comparison_report_task_missing_content(self, mock_comparison_service):
        mock_comparison_service.return_value.get_comparison_for_url.return_value = {"status": "missing_content"}
        result = generate_comparison_report_task(None, "https://example.com")
        assert result["status"] == "missing_content"

    def test_generate_comparison_report_task_duplicate(self, mock_comparison_service):
        mock_comparison_service.return_value.get_comparison_for_url.return_value = {"status": "duplicate"}
        result = generate_comparison_report_task(None, "https://example.com")
        assert result["status"] == "duplicate"

    def test_generate_comparison_report_task_changed(self, mock_comparison_service):
        mock_comparison_service.return_value.get_comparison_for_url.return_value = {
            "status": "changed",
            "info_agregada": ["new_url"],
            "info_eliminada": ["old_url"],
            "estructura_cambio": True
        }
        result = generate_comparison_report_task(None, "https://example.com")
        assert result["status"] == "changed"
        assert "new_url" in result["info_agregada"]
        assert "old_url" in result["info_eliminada"]
        assert result["estructura_cambio"] is True

    from unittest.mock import patch

    @patch("src.apps.shared.tasks.comparison_tasks.ScraperComparisonService")
    def test_generate_comparison_report_task_exception(mock_comparison_service):
        mock_comparison_service.return_value.get_comparison_for_url.side_effect = Exception("Unexpected error")

        result = generate_comparison_report_task.apply(args=["https://example.com"]).result

        assert result["status"] == "error"
        assert "Error interno" in result["message"]

