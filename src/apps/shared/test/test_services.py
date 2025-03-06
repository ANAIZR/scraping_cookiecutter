import pytest
from unittest.mock import patch, MagicMock
from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.utils.services import WebScraperService, ScraperService, ScraperComparisonService


@pytest.mark.django_db
def test_get_expired_urls(mocker):
    # Simulación de los querysets en cadena
    mock_initial_queryset = MagicMock()
    mock_filtered_queryset = MagicMock()
    mock_final_filtered_queryset = MagicMock()
    mock_excluded_queryset = MagicMock()

    # 🔹 Primera llamada a filter()
    mock_initial_queryset.filter.return_value = mock_filtered_queryset

    # 🔹 Segunda llamada a filter()
    mock_filtered_queryset.filter.return_value = mock_final_filtered_queryset

    # 🔹 Llamada a exclude()
    mock_final_filtered_queryset.exclude.return_value = mock_excluded_queryset

    # 🔹 Simular values_list() con el resultado esperado
    mock_excluded_queryset.values_list.return_value = ["https://example.com"]

    # Mock de ScraperURL.objects.filter()
    mock_filter = mocker.patch(
        "src.apps.shared.models.scraperURL.ScraperURL.objects.filter",
        return_value=mock_initial_queryset
    )

    # Ejecutar la función real
    service = WebScraperService()
    result = list(service.get_expired_urls())

    print(f"🔍 Resultado obtenido de get_expired_urls(): {result}")

    # ✅ Verificar que filter() se llamó dos veces
    assert mock_filter.call_count == 2, f"filter() fue llamado {mock_filter.call_count} veces, pero se esperaban 2"
    
    # ✅ Verificar que exclude() se llamó al menos una vez
    assert mock_final_filtered_queryset.exclude.call_count >= 1, "exclude() no fue llamado en get_expired_urls()"

    # ✅ Verificar que el resultado es el esperado
    assert result == ["https://example.com"]



@pytest.mark.django_db
def test_scraper_one_url_success(mocker):
    url = "https://example.com"

    mock_scraper_function = MagicMock(return_value={"data": "Success"})

    with patch.dict("src.apps.shared.utils.scrapers.SCRAPER_FUNCTIONS", {1: mock_scraper_function}):
        scraper_url = ScraperURL.objects.create(url=url, sobrenombre="test", estado_scrapeo="pendiente", mode_scrapeo=1)

        service = WebScraperService()
        result = service.scraper_one_url(url, "test")

        scraper_url.refresh_from_db()

        assert result == {"data": "Success"}
        assert scraper_url.estado_scrapeo == "exitoso"
        assert scraper_url.error_scrapeo == ""

        mock_scraper_function.assert_called_once_with(url, "test")

@pytest.mark.django_db
def test_extract_and_save_species(mocker):
    url = "https://example.com"

    mock_collection = MagicMock()
    mock_collection.find.return_value = [{"_id": "123", "contenido": "test content", "source_url": url}]

    with patch.object(ScraperService, "process_document") as mock_process_document, \
         patch("concurrent.futures.ThreadPoolExecutor") as mock_executor:  # 🔹 Cambio aquí

        service = ScraperService()
        service.collection = mock_collection  
        mock_executor.return_value.__enter__.return_value.submit.side_effect = lambda func, doc: func(doc)

        service.extract_and_save_species(url)

        print(f"🔍 `process_document` fue llamado: {mock_process_document.call_count} veces")

        assert mock_process_document.call_count >= 1

@pytest.mark.django_db
def test_generate_comparison_report(mocker):
    url = "https://example.com"

    # 🔹 Mock de ScraperComparisonService
    mock_comparison_service = mocker.patch("src.apps.shared.utils.services.ScraperComparisonService", autospec=True)
    mock_instance = mock_comparison_service.return_value

    # 🔹 Mock de la colección MongoDB
    mock_collection = MagicMock()
    mock_find = MagicMock()

    # 🔹 Simular la respuesta de find() para devolver un cursor con documentos
    mock_find.sort.return_value = [
        {"_id": "1", "contenido": "old content"},
        {"_id": "2", "contenido": "new content"}
    ]

    # Asignar el mock a la colección
    mock_collection.find.return_value = mock_find
    mock_instance.collection = mock_collection

    # 🔹 Simulación de la función `generate_comparison`
    mock_instance.generate_comparison.return_value = {
        "has_changes": True,
        "info_agregada": ["url1"],
        "info_eliminada": []
    }

    # 🔹 Simulación de `save_or_update_comparison_to_postgres`
    mock_instance.save_or_update_comparison_to_postgres = MagicMock()

    # Ejecutar la función real
    service = ScraperComparisonService()
    result = service.get_comparison_for_url(url)

    print(f"🔍 Resultado obtenido: {result}")

    # ✅ Verificar que la comparación detectó cambios
    assert result["status"] == "changed", f"Resultado inesperado: {result}"

    # ✅ Verificar que `save_or_update_comparison_to_postgres` fue llamado
    mock_instance.save_or_update_comparison_to_postgres.assert_called()

