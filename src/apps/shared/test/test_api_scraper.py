import unittest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status
from src.apps.shared.models.species import CabiSpecies

class TestFullAPI(unittest.TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.mock_scraper_url = MagicMock(url="http://example.com", estado_scrapeo="pendiente")
    
    @patch('src.apps.shared.models.urls.ScraperURL.objects.filter')
    def test_scraper_api_post_success(self, mock_filter):
        # Arrange
        mock_filter.return_value.first.return_value = self.mock_scraper_url
        with patch('src.apps.shared.tasks.scraper_tasks.scraper_url_task.apply_async') as mock_task:
            
            # Act
            response = self.client.post("/scraper-url/", {"url": "http://example.com"}, format='json')
            
            # Assert
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            mock_task.assert_called_once()
    
    @patch('src.apps.shared.models.urls.ScraperURL.objects.filter')
    def test_scraper_api_post_not_found(self, mock_filter):
        # Arrange
        mock_filter.return_value.first.return_value = None
        
        # Act
        response = self.client.post("/scraper-url/", {"url": "http://example.com"}, format='json')
        
        # Assert
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    @patch('src.apps.shared.models.species.Species.objects.filter')
    def test_get_related_species_success(self, mock_filter):
        # Arrange
        mock_species = MagicMock(scientific_name="Test Species", hosts="Host1")
        mock_filter.return_value.exists.return_value = True
        mock_filter.return_value = [mock_species]
        
        # Act
        response = self.client.get("/related_species/Test/")
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn("Test", response.json()["related_species"][0]["scientific_name"])
    
    @patch('src.apps.shared.models.species.Species.objects.filter')
    def test_get_related_species_not_found(self, mock_filter):
        # Arrange
        mock_filter.return_value.exists.return_value = False
        
        # Act
        response = self.client.get("/related/Unknown/")
        
        # Assert
        self.assertEqual(response.status_code, 404)
    
    @patch('src.apps.shared.models.species.CabiSpecies.objects.get')
    @patch('src.apps.shared.models.species.SpeciesNews.objects.filter')
    def test_get_plague_news_success(self, mock_filter, mock_get):
        # Arrange
        mock_get.return_value = MagicMock(scientific_name="Test Species")
        mock_news = MagicMock(summary="News Summary", source_url="http://news.com")
        mock_filter.return_value = [mock_news]
        
        # Act
        response = self.client.get("/api/v1/plague-news/")
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn("News Summary", response.json()[0]["summary"])
    
    @patch('src.apps.shared.models.species.CabiSpecies.objects.get')
    def test_get_plague_news_not_found(self, mock_get):
        # Arrange
        mock_get.side_effect = CabiSpecies.DoesNotExist
        
        # Act
        response = self.client.get("/api/v1/plague-news/999/")
        
        # Assert
        self.assertEqual(response.status_code, 404)
    
    @patch('src.apps.shared.models.species.SpeciesSubscription.objects.filter')
    def test_species_subscription_get(self, mock_filter):
        # Arrange
        mock_subscription = MagicMock(id=1, scientific_name="Test Species")
        mock_filter.return_value = [mock_subscription]
        
        # Act
        response = self.client.get("/api/v1/subscription/")
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn("Test Species", response.json()[0]["scientific_name"])
    
    @patch('src.apps.shared.models.species.SpeciesSubscription.objects.create')
    def test_species_subscription_create(self, mock_create):
        # Arrange
        mock_subscription = MagicMock(id=1, scientific_name="Test Species")
        mock_create.return_value = mock_subscription
        
        # Act
        response = self.client.post("/subscription/", {"scientific_name": "Test Species"}, format='json')
        
        # Assert
        self.assertEqual(response.status_code, 201)
        self.assertIn("Test Species", response.json()["data"]["scientific_name"])

