import unittest
from unittest.mock import patch, MagicMock
from src.apps.shared.tasks.notifications_tasks import check_new_species_task

class TestCheckNewSpeciesTask(unittest.TestCase):
    
    @patch('src.apps.shared.tasks.notifications_tasks.SpeciesNotificationService')
    def test_check_new_species_task(self, mock_service):
        # Arrange
        mock_instance = mock_service.return_value
        
        # Act
        check_new_species_task(None, ["http://example.com"])  # Simulación de ejecución Celery
        
        # Assert
        mock_instance.check_new_news_and_notify.assert_called_once()
