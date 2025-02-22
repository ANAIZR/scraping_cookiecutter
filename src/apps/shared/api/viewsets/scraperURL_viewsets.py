from rest_framework import viewsets
from ...models.scraperURL import (
    ScraperURL,
    Species,
    ReportComparison,
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
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from pymongo import MongoClient
from django.conf import settings

logger = logging.getLogger(__name__)


class ScraperURLViewSet(viewsets.ModelViewSet):
    queryset = ScraperURL.objects.all()
    serializer_class = ScraperURLSerializer


class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Species.objects.select_related("scraper_source").all()
    serializer_class = SpeciesSerializer





class ReportComparisonDetailView(generics.RetrieveAPIView):
    serializer_class = ReportComparisonSerializer

    def get_queryset(self):
        scraper_id = self.kwargs.get("scraper_id")
        scraper_source = get_object_or_404(ScraperURL, id=scraper_id)
        return ReportComparison.objects.filter(scraper_source=scraper_source).order_by("-comparison_date")

    def get_object(self):

        queryset = self.get_queryset()
        return queryset.first()  

    def get_latest_scraping_report(self, scraper_source):

        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]
        collection = db["collection"]

        latest_report = collection.find_one({"url": scraper_source.url}, sort=[("scraping_date", -1)])

        if not latest_report:
            return None
        
        return {
            "message": "Este es el último reporte de scraping.",
            "url": scraper_source.url,
            "scraping_date": latest_report.get("scraping_date"),
            "contenido": latest_report.get("contenido", ""),
        }

    def get(self, request, *args, **kwargs):
        scraper_id = self.kwargs.get("scraper_id")
        scraper_source = get_object_or_404(ScraperURL, id=scraper_id)

        comparison = self.get_object()

        if comparison:
            if not any([comparison.info_agregada, comparison.info_eliminada, comparison.info_modificada]):
                return Response({"message": "No se detectaron cambios nuevos en la comparación."}, status=status.HTTP_200_OK)

            serializer = self.get_serializer(comparison)
            return Response(serializer.data, status=status.HTTP_200_OK)

        latest_scraping_report = self.get_latest_scraping_report(scraper_source)

        if latest_scraping_report:
            return Response(latest_scraping_report, status=status.HTTP_200_OK)

        logger.info(f"❌ No se encontró comparación ni reporte para ScraperURL ID: {scraper_id}")
        return Response({"message": "No se encontró comparación ni reporte para esta URL"}, status=status.HTTP_404_NOT_FOUND)


class SpeciesSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SpeciesSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Permite a los administradores ver todas las suscripciones, pero los usuarios solo pueden ver las suyas."""
        user_id = self.request.query_params.get("user_id")

        if user_id:
            if not self.request.user.is_staff:  # Solo administradores pueden filtrar por user_id
                raise PermissionDenied("No tienes permisos para ver otras suscripciones.")
            return SpeciesSubscription.objects.filter(user_id=user_id).order_by("-created_at")
        
        return SpeciesSubscription.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)  
            return Response(
                {"message": "Filtro guardado exitosamente", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        
        return Response(
            {"error": "Error al guardar la suscripción", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        """Permite eliminar una suscripción solo si pertenece al usuario autenticado."""
        instance = get_object_or_404(SpeciesSubscription, id=kwargs["pk"], user=request.user)
        self.perform_destroy(instance)

        return Response(
            {"message": "Filtro eliminado correctamente"},
            status=status.HTTP_204_NO_CONTENT,
        )