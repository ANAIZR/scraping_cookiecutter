from rest_framework import viewsets
from ...models.scraperURL import (
    ScraperURL,
    Species,
    ReportComparison,
    NotificationSubscription,
    SpeciesSubscription,
)
from ..serializers.scraperURL_serializers import (
    ScraperURLSerializer,
    SpeciesSerializer,
    ReportComparisonSerializer,
    SpeciesSubscriptionSerializer,
)
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from src.apps.shared.models.scraperURL import ScraperURL, ReportComparison
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class ScraperURLViewSet(viewsets.ModelViewSet):
    queryset = ScraperURL.objects.all()
    serializer_class = ScraperURLSerializer


class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Species.objects.select_related("scraper_source").all()
    serializer_class = SpeciesSerializer





class ReportComparisonDetailView(generics.RetrieveAPIView):
    serializer_class = ReportComparisonSerializer

    def get(self, request, *args, **kwargs):
        scraper_id = self.kwargs.get("scraper_id")

        scraper_source = get_object_or_404(ScraperURL, id=scraper_id)

        comparison = (
            ReportComparison.objects.filter(scraper_source=scraper_source)
            .order_by("-comparison_date")
            .first()
        )

        if not comparison:
            logger.info(f"No se encontró comparación para el ScraperURL ID: {scraper_id}")
            return Response(
                {"message": "No se encontró comparación para esta URL"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not comparison.info_agregada and not comparison.info_eliminada and not comparison.info_modificada:
            return Response(
                {"message": "No se detectaron cambios nuevos en la comparación."},
                status=status.HTTP_200_OK,
            )

        serializer = ReportComparisonSerializer(comparison)
        return Response(serializer.data, status=status.HTTP_200_OK)



class SpeciesSubscriptionViewSet(viewsets.ModelViewSet):

    serializer_class = SpeciesSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SpeciesSubscription.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):

        request.data["user"] = (
            request.user.id
        )  
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Filtro guardado exitosamente", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):

        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Filtro eliminado correctamente"},
            status=status.HTTP_204_NO_CONTENT,
        )
