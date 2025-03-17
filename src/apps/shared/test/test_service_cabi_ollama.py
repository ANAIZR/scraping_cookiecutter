import unittest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.cabi_ollama_service import OllamaCabiService
from bson.objectid import ObjectId


class TestOllamaCabiService(unittest.TestCase):
    
    def setUp(self):
        self.service = OllamaCabiService()
        self.mock_mongo = MagicMock()
        self.service.collection = self.mock_mongo

    @patch('src.apps.shared.services.cabi_ollama_service.MongoClient')
    def test_extract_and_save_species_no_documents(self, mock_mongo_client):
        # Arrange
        self.mock_mongo.find.return_value = []
        
        # Act
        self.service.extract_and_save_species("http://example.com")
        
        # Assert
        self.mock_mongo.find.assert_called_once_with({"url": "http://example.com", "processed": {"$ne": True}})

    @patch('src.apps.shared.services.cabi_ollama_service.MongoClient')
    def test_process_document_not_found(self, mock_mongo_client):
        # Arrange
        self.mock_mongo.find_one.return_value = None
        
        # Act
        self.service.process_document(ObjectId())
        
        # Assert
        self.mock_mongo.find_one.assert_called()

    @patch('src.apps.shared.services.cabi_ollama_service.requests.post')
    def test_analyze_content_with_ollama_successful(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"message": {"content": "{\"symptoms\": \"Example\", \"impact\": \"High\"}"}}'
        ]
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        fields_to_summarize = {"symptoms": "Example symptoms", "impact": "High impact"}
        source_url = "http://example.com"

        # Act
        result = self.service.analyze_content_with_ollama(fields_to_summarize, source_url)

        # Debugging
        print("🔍 Respuesta de analyze_content_with_ollama:", result)

        # Assert
        self.assertIsInstance(result, dict)  # Verifica que devuelve un diccionario
        self.assertIn("symptoms", result)  # Verifica que la clave está presente
        self.assertEqual(result["symptoms"], "Example")
        self.assertEqual(result["impact"], "High")

        mock_post.assert_called()


    @patch('src.apps.shared.services.cabi_ollama_service.CabiSpecies.objects.update_or_create')
    def test_save_species_to_postgres(self, mock_update_or_create):
        # Arrange
        structured_data = {"scientific_name": "Test Species", "source_url": "http://example.com"}
        mock_update_or_create.return_value = (MagicMock(scientific_name="Test Species"), True)
        
        # Act
        self.service.save_species_to_postgres(structured_data, ObjectId())
        
        # Assert
        mock_update_or_create.assert_called()

    def test_datos_son_validos(self):
        # Arrange
        valid_data = {"scientific_name": "Valid Species", "common_names": "Example"}
        invalid_data = {"scientific_name": "", "common_names": ""}
        
        # Act & Assert
        self.assertTrue(self.service.datos_son_validos(valid_data))
        self.assertFalse(self.service.datos_son_validos(invalid_data))

