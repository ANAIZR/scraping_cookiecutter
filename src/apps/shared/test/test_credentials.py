import pytest
from unittest.mock import patch, MagicMock
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.apps.shared.utils.credentials import login_cabi_scienceconnect

@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.get = MagicMock()
    driver.find_element = MagicMock()
    return driver

@patch("selenium.webdriver.support.ui.WebDriverWait.until")
def test_login_cabi_scienceconnect_success(mock_wait, mock_driver):
    mock_element = MagicMock()
    mock_element.send_keys = MagicMock()
    mock_element.submit = MagicMock()
    mock_wait.side_effect = lambda *args, **kwargs: mock_element
    
    result = login_cabi_scienceconnect(mock_driver)
    
    assert result is True
    mock_driver.get.assert_called_with("https://cabi.scienceconnect.io/login")
    mock_element.send_keys.assert_called()
    mock_element.submit.assert_called()

@patch("selenium.webdriver.support.ui.WebDriverWait.until")
def test_login_cabi_scienceconnect_failure(mock_wait, mock_driver):
    mock_wait.side_effect = Exception("Timeout")
    result = login_cabi_scienceconnect(mock_driver)
    assert result is False
