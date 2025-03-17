import unittest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.news_services import NewsScraperService
from bson.objectid import ObjectId

class TestNewsScraperService(unittest.TestCase):
    
    def setUp(self):
        self.service = NewsScraperService()
        self.mock_mongo = MagicMock()
        self.service.collection = self.mock_mongo

    @patch('src.apps.shared.services.news_services.MongoClient')
    def test_extract_and_save_species_no_documents(self, mock_mongo_client):
        # Arrange
        self.mock_mongo.find.return_value = []
        
        # Act
        self.service.extract_and_save_species("http://example.com")
        
        # Assert
        self.mock_mongo.find.assert_called_once_with({"url": "http://example.com", "processed": {"$ne": True}})

    @patch('src.apps.shared.services.news_services.MongoClient')
    def test_process_news_document_not_found(self, mock_mongo_client):
        # Arrange
        self.mock_mongo.find_one.return_value = None
        
        # Act
        self.service.process_news_document({"_id": ObjectId()})
        
        # Assert
        self.mock_mongo.find_one.assert_called()

    @patch('src.apps.shared.services.news_services.requests.post')
    def test_text_to_json_successful(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [b'{"message": {"content": "{\"nombre_cientifico\": \"Example Species\"}"}}']
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        content = "This is a news content."
        source_url = "http://example.com"
        url = "http://news-source.com"
        
        # Act
        result = self.service.text_to_json(content, source_url, url)
        
        # Assert
        self.assertEqual(result["nombre_cientifico"], "Example Species")
        mock_post.assert_called()

    @patch('src.apps.shared.services.news_services.SpeciesNews.objects.update_or_create')
    def test_save_news_to_postgres(self, mock_update_or_create):
        # Arrange
        structured_data = {"nombre_cientifico": "Test Species", "source_url": "http://example.com"}
        mock_update_or_create.return_value = (MagicMock(source_url="http://example.com"), True)
        
        # Act
        self.service.save_news_to_postgres(structured_data, "http://example.com", "http://news-source.com", ObjectId())
        
        # Assert
        mock_update_or_create.assert_called()

    def test_datos_son_validos(self):
        # Arrange
        valid_data = {"nombre_cientifico": "Valid Species", "distribucion": "Region1, Region2"}
        invalid_data = {"nombre_cientifico": "", "distribucion": ""}
        
        # Act & Assert
        self.assertTrue(self.service.datos_son_validos(valid_data))
        self.assertFalse(self.service.datos_son_validos(invalid_data))

