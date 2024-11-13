from rest_framework import viewsets
from ...models.scraper import ScraperURL
from ..serializers.url_serializers import ScraperURLSerializer


class ScraperURLViewSet(viewsets.ModelViewSet):
    queryset = ScraperURL.objects.all()
    serializer_class = ScraperURLSerializer
