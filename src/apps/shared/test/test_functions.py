import pytest
import os
from src.apps.shared.utils.functions import load_keywords, generate_directory
from unittest.mock import patch, MagicMock
import pytest
from src.apps.shared.utils.functions import connect_to_mongo
from unittest.mock import patch
import pytest
from src.apps.shared.utils.functions import initialize_driver
import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.utils.functions import extract_text_from_pdf

@pytest.mark.django_db
def test_generate_directory_creates_folder():
    url = "https://example.com"
    folder_path = generate_directory(url)
    assert os.path.exists(folder_path)




@patch("src.apps.shared.utils.functions.uc.Chrome")
def test_initialize_driver(mock_chrome):
    driver = initialize_driver()
    assert driver is not None
    mock_chrome.assert_called_once()


@patch("src.apps.shared.utils.functions.MongoClient")
def test_connect_to_mongo(mock_mongo_client):
    db_mock = MagicMock()
    collection_mock = MagicMock()
    mock_mongo_client.return_value.__getitem__.return_value = db_mock
    db_mock.__getitem__.return_value = collection_mock

    collection, fs = connect_to_mongo("test_db", "test_collection")
    assert collection is not None
    assert fs is not None



@patch("src.apps.shared.utils.functions.requests.get")
@patch("src.apps.shared.utils.functions.PyPDF2.PdfReader")
def test_extract_text_from_pdf(mock_pdf_reader, mock_requests):
    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 Fake PDF Data"
    mock_requests.return_value = mock_response

    mock_pdf_instance = MagicMock()
    mock_pdf_instance.pages = [MagicMock()]
    mock_pdf_instance.pages[0].extract_text.return_value = "Test PDF Content"
    mock_pdf_reader.return_value = mock_pdf_instance

    pdf_text = extract_text_from_pdf("http://example.com/sample.pdf")
    assert pdf_text == "Test PDF Content"
