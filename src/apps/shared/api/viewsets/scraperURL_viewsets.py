from rest_framework import viewsets
from ...models.scraperURL import ScraperURL, Species
from ..serializers.scraperURL_serializers import ScraperURLSerializer, SpeciesSerializer


class ScraperURLViewSet(viewsets.ModelViewSet):
    queryset = ScraperURL.objects.all()
    serializer_class = ScraperURLSerializer
class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):  
    queryset = Species.objects.all()
    serializer_class = SpeciesSerializer