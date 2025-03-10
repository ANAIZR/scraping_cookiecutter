import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.notifications import SpeciesNotificationService

@pytest.mark.django_db
class TestSpeciesNotificationService:

    @pytest.fixture
    def mock_email_service(self):
        with patch('src.apps.shared.services.notifications.EmailService.send_email') as mock:
            yield mock

    @pytest.fixture
    def mock_species(self):
        with patch('src.apps.shared.models.Species.objects') as mock:
            yield mock

    @pytest.fixture
    def mock_subscription(self):
        with patch('src.apps.shared.models.SpeciesSubscription.objects') as mock:
            yield mock

    def test_check_new_species_and_notify_no_new_species(self, mock_species, mock_subscription, mock_email_service):
        mock_species.filter.return_value.exists.return_value = False

        service = SpeciesNotificationService()
        service.check_new_species_and_notify(['https://example.com'])

        mock_email_service.assert_not_called()

    def test_check_new_species_and_notify_with_matches(self, mock_species, mock_subscription, mock_email_service):
        mock_species_instance = MagicMock()
        mock_species_instance.exists.return_value = True

        mock_species.filter.return_value = mock_species_instance
        mock_subscription.filter.return_value = [MagicMock(user=MagicMock(email='user@example.com'),
                                                           scientific_name='Test',
                                                           distribution='',
                                                           hosts='')]

        service = SpeciesNotificationService()
        service.filter_species_by_subscription = MagicMock(return_value=mock_species_instance)

        mock_species_instance.__iter__.return_value = [
            MagicMock(scientific_name='Test Species', source_url='https://example.com/species/1')
        ]

        service.check_new_species_and_notify(['https://example.com'])

        mock_email_service.assert_called_once()
        args, kwargs = mock_email_service.call_args

        assert '🔔 Se han añadido 1 nuevos registros' in args[0]
        assert ['user@example.com'] == args[1]
        assert 'Test Species - https://example.com/species/1' in args[2]

    def test_filter_species_by_subscription(self):
        service = SpeciesNotificationService()

        species_mock = MagicMock()
        subscription_mock = MagicMock(scientific_name='SpeciesX', distribution='Peru', hosts='HostY')

        service.filter_species_by_subscription(species_mock, subscription_mock)

        species_mock.filter.assert_any_call(scientific_name__icontains='SpeciesX')
        species_mock.filter.assert_any_call(distribution__icontains='Peru')
        species_mock.filter.assert_any_call(hosts__icontains='HostY')