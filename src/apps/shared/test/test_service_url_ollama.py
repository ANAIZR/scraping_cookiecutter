import unittest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.urls_ollama_service import OllamaService
from src.apps.shared.models.urls import ScraperURL
from pymongo import MongoClient
from django.conf import settings
from django.test import TestCase

class TestOllamaService(TestCase):
    
    def setUp(self):
        self.service = OllamaService()
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["urls_scraper"]

    @patch('src.apps.shared.services.urls_ollama_service.MongoClient')
    def test_extract_and_save_species_no_documents(self, mock_mongo_client):
        # Arrange
        self.collection.find.return_value = []
        
        # Act
        self.service.extract_and_save_species("http://example.com")
        
        # Assert
        self.collection.find.assert_called_once()

    @patch('src.apps.shared.services.urls_ollama_service.MongoClient')
    def test_process_document_not_found(self, mock_mongo_client):
        # Arrange
        self.collection.find_one.return_value = None
        
        # Act
        self.service.process_document({"_id": "id1"})
        
        # Assert
        self.collection.find_one.assert_called()

    @patch('src.apps.shared.services.urls_ollama_service.requests.post')
    def test_text_to_json_successful(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [b'{"message": {"content": "{\"nombre_cientifico\": \"Example Species\"}"}}']
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        content = "Sample text content."
        source_url = "http://example.com"
        url = "http://source.com"
        
        # Act
        result = self.service.text_to_json(content, source_url, url)
        
        # Assert
        self.assertEqual(result["nombre_cientifico"], "Example Species")
        mock_post.assert_called()

    @patch('src.apps.shared.services.urls_ollama_service.Species.objects.update_or_create')
    @patch('src.apps.shared.services.urls_ollama_service.ScraperURL.objects.get')
    def test_save_species_to_postgres(self, mock_get_scraper, mock_update_or_create):
        # Arrange
        structured_data = {"nombre_cientifico": "Test Species", "source_url": "http://example.com"}
        mock_update_or_create.return_value = (MagicMock(scientific_name="Test Species"), True)
        
        # Act
        self.service.save_species_to_postgres(structured_data, "http://example.com", "http://source.com", "id1")
        
        # Assert
        mock_update_or_create.assert_called()

    def test_datos_son_validos(self):
        # Arrange
        valid_data = {"nombre_cientifico": "Valid Species", "distribucion": "Region1, Region2"}
        invalid_data = {"nombre_cientifico": "", "distribucion": ""}
        
        # Act & Assert
        self.assertTrue(self.service.datos_son_validos(valid_data))
        self.assertFalse(self.service.datos_son_validos(invalid_data))

    def test_full_integration_extract_and_save_species(self):
        # Arrange
        scraper = ScraperURL.objects.create(url="http://example.com")
        self.collection.insert_one({"_id": "id1", "contenido": "Sample content", "url": "http://example.com", "processed": False})
        
        # Act
        self.service.extract_and_save_species("http://example.com")
        
        # Assert
        processed_doc = self.collection.find_one({"_id": "id1"})
        self.assertTrue(processed_doc["processed"])
