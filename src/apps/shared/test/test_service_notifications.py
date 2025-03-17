import unittest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from src.apps.shared.services.notifications_service import SpeciesNotificationService

class TestSpeciesNotificationService(unittest.TestCase):
    
    def setUp(self):
        self.service = SpeciesNotificationService()
        self.service.now = timezone.now()
        self.service.last_scraping_time = self.service.now - timedelta(hours=1)

    @patch('src.apps.shared.services.notifications_service.SpeciesNews.objects.filter')
    def test_check_new_news_and_notify_no_news(self, mock_news_filter):
        # Arrange
        mock_news_filter.return_value.exists.return_value = False
        
        # Act
        self.service.check_new_news_and_notify()
        
        # Assert
        mock_news_filter.assert_called_once()

    @patch('src.apps.shared.services.notifications_service.SpeciesNews.objects.filter')
    @patch('src.apps.shared.services.notifications_service.SpeciesSubscription.objects.filter')
    def test_check_new_news_and_notify_with_news(self, mock_subscriptions_filter, mock_news_filter):
        # Arrange
        mock_news = MagicMock()
        mock_news.exists.return_value = True
        mock_news.values_list.return_value = ["Species A", "Species B"]
        
        mock_subscription = MagicMock()
        mock_subscription.user.email = "user@example.com"
        mock_subscription.scientific_name = "Species A"
        
        mock_news_filter.return_value = mock_news
        mock_subscriptions_filter.return_value = [mock_subscription]
        
        # Act
        with patch.object(self.service, 'notify_user_of_new_news') as mock_notify:
            self.service.check_new_news_and_notify()
            
            # Assert
            mock_notify.assert_called_once_with(mock_subscription.user, mock_subscription, mock_news.filter())

    @patch('src.apps.shared.services.notifications_service.EmailService.send_email')
    def test_notify_user_of_new_news(self, mock_send_email):
        # Arrange
        user = MagicMock()
        user.email = "user@example.com"
        subscription = MagicMock()
        subscription.scientific_name = "Species A"
        news = [MagicMock(publication_date="2024-03-17", source_url="http://example.com", summary="New discovery!")]
        
        # Act
        self.service.notify_user_of_new_news(user, subscription, news)
        
        # Assert
        mock_send_email.assert_called_once()
        
