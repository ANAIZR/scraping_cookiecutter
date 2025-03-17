import unittest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.urls_ollama_service import OllamaService
from src.apps.shared.models.urls import ScraperURL
from pymongo import MongoClient
from django.conf import settings
from django.test import TestCase
from bson.objectid import ObjectId

from src.apps.shared.services.urls_ollama_service import datos_son_validos
class TestOllamaService(TestCase):
    
    def setUp(self):
        self.service = OllamaService()
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["urls_scraper"]

    @patch('src.apps.shared.services.urls_ollama_service.MongoClient')
    def test_extract_and_save_species_no_documents(self, mock_mongo_client):
        # Arrange
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        # Configurar la estructura de MongoDB Mock
        mock_mongo_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection

        # Simular que `find` retorna una lista vacía
        mock_collection.find.return_value = []

        # Asignar el mock de `MongoClient` a `self.service`
        self.service.client = mock_client
        self.service.db = mock_db
        self.service.collection = mock_collection

        # Act
        self.service.extract_and_save_species("http://example.com")

        # Assert
        mock_collection.find.assert_called_once_with({"url": "http://example.com", "processed": {"$ne": True}})



    @patch('src.apps.shared.services.urls_ollama_service.MongoClient')
    def test_process_document_not_found(self, mock_mongo_client):
        # Arrange
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        # Configurar la estructura de MongoDB Mock
        mock_mongo_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection

        # Simular que `find_one` retorna None (documento no encontrado)
        mock_collection.find_one.return_value = None

        # Asignar el mock de `MongoClient` a `self.service`
        self.service.client = mock_client
        self.service.db = mock_db
        self.service.collection = mock_collection

        # Act
        self.service.process_document(ObjectId("65c7b3b9e2a8c3f84c9e4f1e"))  # Usar un ObjectId válido

        # Assert
        mock_collection.find_one.assert_called_once()


    @patch('src.apps.shared.services.urls_ollama_service.requests.post')
    def test_text_to_json_successful(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"message": {"content": "{\\"nombre_cientifico\\": \\"Example Species\\"}"}}'
        ]
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        content = "Sample text content."
        source_url = "http://example.com"
        url = "http://source.com"

        # Act
        result = self.service.text_to_json(content, source_url, url)

        # Debugging: Imprimir la respuesta obtenida
        print("🔍 JSON Extraído:", result)

        # Assert
        self.assertIsNotNone(result, "El resultado de text_to_json no debe ser None")
        self.assertIn("nombre_cientifico", result, "Debe contener la clave 'nombre_cientifico'")
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
        self.assertTrue(datos_son_validos(valid_data))  # Llamar directamente a la función global
        self.assertFalse(datos_son_validos(invalid_data))


    def test_full_integration_extract_and_save_species(self):
        # Arrange
        scraper = ScraperURL.objects.create(url="http://example.com")
        mongo_id = ObjectId()  # Generar un ObjectId válido

        self.collection.insert_one({
            "_id": mongo_id,  
            "contenido": "Sample content",
            "url": "http://example.com",
            "processed": False
        })

        # Act
        self.service.extract_and_save_species("http://example.com")

        # Assert
        processed_doc = self.collection.find_one({"_id": mongo_id})
        print("🔍 Documento después del procesamiento:", processed_doc)  # Debugging
        self.assertTrue(processed_doc["processed"])
