from rest_framework import viewsets
from ...models.scraperURL import ScraperURL, Species, ReportComparison
from ..serializers.scraperURL_serializers import ScraperURLSerializer, SpeciesSerializer, ReportComparisonSerializer


class ScraperURLViewSet(viewsets.ModelViewSet):
    queryset = ScraperURL.objects.all()
    serializer_class = ScraperURLSerializer
class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):  
    queryset = Species.objects.select_related('scraper_source').all()
    serializer_class = SpeciesSerializer
class ReportComparisonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReportComparison.objects.select_related("scraper_source").all()
    serializer_class = ReportComparisonSerializer