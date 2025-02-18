import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def disable_celery():
    with patch("src.apps.shared.utils.tasks.scraper_url_task.apply_async") as mock_apply_async:
        mock_apply_async.return_value = None
        yield
