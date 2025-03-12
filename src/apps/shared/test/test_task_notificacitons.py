import pytest
from src.apps.shared.tasks.notifications_tasks import check_new_species_task

class TestCheckNewSpeciesTask:

    @pytest.fixture
    def mock_notification_service(self, mocker):
        return mocker.patch('src.apps.shared.services.notifications.SpeciesNotificationService')

    def test_check_new_species_task(self, mock_notification_service):
        mock_instance = mock_notification_service.return_value
        mock_instance.check_new_species_and_notify.return_value = []  # ✅ Evita el error de iteración sobre None

        urls = ["https://example.com/species1", "https://example.com/species2"]
        check_new_species_task(None, urls)  # Llama a la tarea con URLs

        mock_instance.check_new_species_and_notify.assert_called_once_with(urls)
