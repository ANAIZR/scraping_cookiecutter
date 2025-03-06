import pytest
from unittest.mock import patch, MagicMock
from celery.exceptions import Retry
from src.apps.shared.utils.tasks import (
    scraper_url_task,
    check_new_species_task,
    process_scraped_data_task,
    generate_comparison_report_task,
    scraper_expired_urls_task,
)
from src.apps.shared.models.scraperURL import ScraperURL
from django.utils import timezone

@pytest.mark.django_db
def test_scraper_url_task_success(mocker):
    url = "https://example.com"
    mock_scraper_service = mocker.patch("src.apps.shared.utils.services.WebScraperService")
    mock_scraper_service.return_value.scraper_one_url.return_value = {"data": "Scraped Data"}
    
    scraper_url = ScraperURL.objects.create(
        url=url, sobrenombre="test", estado_scrapeo="pendiente"
    )
    
    result = scraper_url_task(url)
    scraper_url.refresh_from_db()
    
    assert result["status"] == "exitoso"
    assert scraper_url.estado_scrapeo == "exitoso"
    assert scraper_url.error_scrapeo == ""

@pytest.mark.django_db
def test_scraper_url_task_failure(mocker):
    url = "https://example.com"

    # 🔹 Mock de WebScraperService
    mock_scraper_service = mocker.patch("src.apps.shared.utils.services.WebScraperService", autospec=True)
    mock_instance = mock_scraper_service.return_value

    # 🔹 Simular fallo en `scraper_one_url`
    mock_instance.scraper_one_url.return_value = {"error": "Scraping failed"}

    # 🔹 Crear instancia en BD con estado "pendiente"
    scraper_url = ScraperURL.objects.create(url=url, sobrenombre="test", estado_scrapeo="pendiente")

    # 🔹 Ejecutar la tarea
    result = scraper_url_task(url)

    # 🔹 Refrescar el objeto desde BD
    scraper_url.refresh_from_db()

    # 🔍 Depuración: Imprimir resultados
    print(f"🔍 Resultado de `scraper_url_task`: {result}")
    print(f"📌 Estado en BD: {scraper_url.estado_scrapeo}, Error: {scraper_url.error_scrapeo}")

    # ✅ Verificar que el `scraper_url_task` falló correctamente
    assert result["status"] == "failed", f"Estado esperado: 'failed', obtenido: {result['status']}"
    assert scraper_url.estado_scrapeo == "fallido", f"Estado esperado: 'fallido', obtenido: {scraper_url.estado_scrapeo}"
    assert scraper_url.error_scrapeo == "Scraping failed", f"Error esperado: 'Scraping failed', obtenido: {scraper_url.error_scrapeo}"

    # ✅ Asegurar que `scraper_one_url` fue llamado correctamente
    mock_instance.scraper_one_url.assert_called_once_with(url, "test")

@pytest.mark.django_db
def test_check_new_species_task(mocker):
    mock_check_new_species = mocker.patch("src.apps.shared.utils.tasks.check_new_species_and_notify")

    urls = ["https://example.com"]
    check_new_species_task(urls)

    mock_check_new_species.assert_called_once_with(urls)


@pytest.mark.django_db
def test_process_scraped_data_task(mocker):
    url = "https://example.com"

    # 🔹 Mock de `ScraperService`
    mock_scraper_service = mocker.patch("src.apps.shared.utils.tasks.ScraperService", autospec=True)
    mock_scraper_service_instance = mock_scraper_service.return_value

    # 🔹 Mock de `check_new_species_and_notify`
    mock_check_notify = mocker.patch("src.apps.shared.utils.tasks.check_new_species_and_notify")

    # 🔹 Ejecutar la tarea
    process_scraped_data_task(url)

    # ✅ Verificar que `extract_and_save_species` fue llamado correctamente
    mock_scraper_service_instance.extract_and_save_species.assert_called_once_with(url)

    # ✅ Verificar que `check_new_species_and_notify` fue llamado con la lista de URLs
    mock_check_notify.assert_called_once_with([url])

@pytest.mark.django_db
def test_generate_comparison_report_task(mocker):
    url = "https://example.com"

    with patch("src.apps.shared.utils.services.ScraperComparisonService.get_comparison_for_url") as mock_get_comparison:
        mock_get_comparison.return_value = {"status": "changed"}

        result = generate_comparison_report_task(url)

        print(f"🔍 Resultado obtenido: {result}")  

        assert result["status"] == "changed"
@pytest.mark.django_db
def test_scraper_expired_urls_task(mocker):
    # 🔹 Ajuste en el patch de `WebScraperService`
    mock_scraper_service = mocker.patch("src.apps.shared.utils.tasks.WebScraperService", autospec=True)
    mock_scraper_service_instance = mock_scraper_service.return_value
    mock_scraper_service_instance.get_expired_urls.return_value = ["https://example.com"]

    # Mock de Celery tasks
    mock_scraper_task = mocker.patch("src.apps.shared.utils.tasks.scraper_url_task.si")
    mock_chain = mocker.patch("src.apps.shared.utils.tasks.chain")

    # Ejecutar la tarea
    scraper_expired_urls_task()

    # Verificar llamadas esperadas
    mock_scraper_service_instance.get_expired_urls.assert_called_once()
    mock_scraper_task.assert_called_once_with("https://example.com")
    mock_chain.assert_called()

