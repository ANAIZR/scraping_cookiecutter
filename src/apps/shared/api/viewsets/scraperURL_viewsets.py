from rest_framework import viewsets
from ...models.scraperURL import ScraperURL, Species, ReportComparison, NotificationSubscription
from ..serializers.scraperURL_serializers import ScraperURLSerializer, SpeciesSerializer, ReportComparisonSerializer
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from src.apps.shared.models.scraperURL import ScraperURL, ReportComparison
import logging
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework import status
from rest_framework.views import APIView


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
    
@method_decorator(login_required, name='dispatch')
class ToggleNotificationAPIView(APIView):

    def post(self, request):

        scraper_url_id = request.data.get("scraper_url_id")

        if not scraper_url_id:
            return Response({"success": False, "message": "ID de URL no proporcionado"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            scraper_url = ScraperURL.objects.get(id=scraper_url_id)
        except ScraperURL.DoesNotExist:
            return Response({"success": False, "message": "URL no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        subscription, created = NotificationSubscription.objects.get_or_create(user=request.user, scraper_url=scraper_url)

        if not created:  
            subscription.delete()
            return Response({"success": True, "message": "Notificación desactivada"}, status=status.HTTP_200_OK)

        return Response({"success": True, "message": "Notificación activada"}, status=status.HTTP_201_CREATED)