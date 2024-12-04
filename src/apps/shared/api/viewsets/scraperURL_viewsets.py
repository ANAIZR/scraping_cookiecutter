from rest_framework import viewsets
from ...models.scraperURL import ScraperURL
from ..serializers.scraperURL_serializers import ScraperURLSerializer


class ScraperURLViewSet(viewsets.ModelViewSet):
    queryset = ScraperURL.objects.all()
    serializer_class = ScraperURLSerializer
