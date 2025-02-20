from rest_framework import viewsets
from ...models.scraperURL import ScraperURL, Species, ReportComparison
from ..serializers.scraperURL_serializers import ScraperURLSerializer, SpeciesSerializer, ReportComparisonSerializer
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from src.apps.shared.models.scraperURL import ScraperURL, ReportComparison
import logging
logger = logging.getLogger(__name__)

class ScraperURLViewSet(viewsets.ModelViewSet):
    queryset = ScraperURL.objects.all()
    serializer_class = ScraperURLSerializer
class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):  
    queryset = Species.objects.select_related('scraper_source').all()
    serializer_class = SpeciesSerializer
class ReportComparisonDetailView(generics.RetrieveAPIView):
    serializer_class = ReportComparisonSerializer

    def get(self, request, *args, **kwargs):
        scraper_id = self.kwargs.get("scraper_id") 

        scraper_source = get_object_or_404(ScraperURL, id=scraper_id)

        comparison = ReportComparison.objects.filter(scraper_source=scraper_source).order_by("-comparison_date").first()

        if not comparison:
            logger.info(f"No se encontró comparación para el ScraperURL ID: {scraper_id}")
            return Response({"message": "No se encontró comparación para esta URL"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ReportComparisonSerializer(comparison)
        return Response(serializer.data, status=status.HTTP_200_OK)