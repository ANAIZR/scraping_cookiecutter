import unittest
from unittest.mock import patch, MagicMock
from src.apps.shared.services.resume_service import ResumeService
from src.apps.shared.models.species import CabiSpecies, Species
from src.apps.shared.models.urls import ScraperURL
from django.test import TestCase

class TestResumeService(TestCase):
    
    def setUp(self):
        self.service = ResumeService()

    @patch('src.apps.shared.services.resume_service.CabiSpecies.objects.get')
    def test_get_plague_summary_species_not_found(self, mock_cabi_get):
        # Arrange
        mock_cabi_get.side_effect = CabiSpecies.DoesNotExist
        
        # Act
        result = self.service.get_plague_summary(1)
        
        # Assert
        self.assertIsNone(result)


    @patch('src.apps.shared.services.resume_service.CabiSpecies.objects.get')
    @patch('src.apps.shared.services.resume_service.Species.objects.filter')
    @patch('src.apps.shared.services.resume_service.ScraperURL.objects.all')
    def test_get_plague_summary_with_data(self, mock_scraper_all, mock_species_filter, mock_cabi_get):
        # Arrange
        mock_cabi_species = MagicMock()
        mock_cabi_species.scientific_name = "Test Species"
        mock_cabi_get.return_value = mock_cabi_species

        # Simula un objeto Species con un queryset
        mock_species = MagicMock()
        mock_species_queryset = MagicMock()
        mock_species_queryset.filter.return_value = mock_species_queryset
        mock_species_queryset.exclude.return_value = mock_species

        # Simulación de `values_list()` correctamente implementada
        def values_list_mock(field, flat):
            data = {
                "hosts": ["Host1"], 
                "distribution": ["Region1"], 
                "environmental_conditions": ["Climate1"]
            }
            return data.get(field, [])  # Devuelve la lista correcta

        mock_species.values_list.side_effect = values_list_mock
        mock_species_filter.return_value = mock_species_queryset

        # Simula ScraperURL.objects.all()
        mock_scraper = MagicMock()
        mock_scraper.id = 1
        mock_scraper.url = "http://scraper.com"
        mock_scraper_all.return_value = [mock_scraper]

        # Act
        result = self.service.get_plague_summary(1)

        # Debugging: Verificar resultado obtenido
        print("🔍 Resultado de get_plague_summary:", result)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["hosts"], "Host1")
        self.assertEqual(result[0]["distribution"], "Region1")
        self.assertEqual(result[0]["climatic_variables"], "Climate1")



    def test_integration_get_plague_summary(self):
        # Arrange
        cabi_species = CabiSpecies.objects.create(scientific_name="Test Species")
        scraper = ScraperURL.objects.create(url="http://scraper.com")
        species = Species.objects.create(scientific_name="Test Species", scraper_source=scraper, hosts="Host1", distribution="Region1", environmental_conditions="Climate1")
        
        # Act
        result = self.service.get_plague_summary(cabi_species.id)
        
        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["hosts"], "Host1")
        self.assertEqual(result[0]["distribution"], "Region1")
        self.assertEqual(result[0]["climatic_variables"], "Climate1")

