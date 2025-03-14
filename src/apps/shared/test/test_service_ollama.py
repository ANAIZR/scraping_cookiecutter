import pytest
from unittest.mock import patch, MagicMock
from apps.shared.services.urls_ollama_service import OllamaService
from django.conf import settings

class TestOllamaService:

    @pytest.fixture
    def mock_mongo_collection(self, mocker):
        mock_client = mocker.patch('src.apps.shared.services.ollama.MongoClient')
        mock_db = mock_client.return_value.__getitem__.return_value
        mock_collection = mock_db.__getitem__.return_value
        return mock_collection

    @pytest.fixture
    def mock_requests_post(self, mocker):
        return mocker.patch('src.apps.shared.services.ollama.requests.post')

    def test_extract_and_save_species_no_documents(self, mock_mongo_collection):
        mock_mongo_collection.find.return_value = []
        service = OllamaService()
        service.extract_and_save_species("https://example.com")

        mock_mongo_collection.find.assert_called_once()


    @patch("src.apps.shared.services.ollama.MongoClient")
    def test_process_document_already_processed(self, mock_mongo_client):
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_mongo_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection

        mock_collection.find_one.return_value = {"_id": "123", "processed": True}

        service = OllamaService()
        service.collection = mock_collection  

        service.text_to_json = MagicMock()

        doc = {"_id": "123", "contenido": "sample content", "source_url": "https://example.com"}

        service.process_document(doc)

        mock_collection.find_one.assert_called_once_with({"_id": "123"})
        service.text_to_json.assert_not_called()  




    def test_process_document_invalid_json(self, mocker, mock_mongo_collection):
        mock_mongo_collection.find_one.return_value = None
        mocker.patch.object(OllamaService, 'text_to_json', return_value=None)

        service = OllamaService()
        doc = {"_id": "456", "contenido": "contenido invalido", "source_url": "https://example.com"}
        service.process_document(doc)

        mock_mongo_collection.update_one.assert_not_called()

    def test_text_to_json_success(self, mocker):
        mock_response = mocker.Mock()
        mock_response.iter_lines.return_value = [
            b'{"message": {"content": "{\\"nombre_cientifico\\": \\"Species Test\\"}"}}'
        ]
        
        mocker.patch('requests.post', return_value=mock_response)

        service = OllamaService()
        result = service.text_to_json("contenido válido", "https://source.com", "https://example.com")

        print(f"Resultado de text_to_json: {result}") 

        assert isinstance(result, dict), "El resultado no es un diccionario"
        assert result.get("nombre_cientifico") is not None, "El campo 'nombre_cientifico' no está en el resultado"


    def test_text_to_json_invalid_response(self, mocker):
        mock_response = mocker.Mock()
        mock_response.iter_lines.return_value = [b'invalid json']
        mocker.patch('requests.post', return_value=mock_response)

        service = OllamaService()
        result = service.text_to_json("contenido inválido", "https://source.com", "https://example.com")

        assert result is None
