from rest_framework import viewsets
from ...models.species import Species, ReportComparison, SpeciesSubscription,CabiSpecies, SpeciesNews
from ...models.urls import ScraperURL
from ..serializers.scraperURL_serializers import ScraperURLSerializer
from ..serializers.species_serializers import SpeciesCabiSerializer,SpeciesSerializer, ReportComparisonSerializer, SpeciesSubscriptionSerializer, SpeciesNewsSerializer
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from src.apps.shared.models.species import  ReportComparison
from src.apps.shared.models.urls import ScraperURL
import logging
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from pymongo import MongoClient
from django.conf import settings
from src.apps.users.services.email import EmailService
from rest_framework.pagination import PageNumberPagination
from urllib.parse import unquote  
from django.http import JsonResponse
from django.db.models import Q
from src.apps.shared.services.resume_service import ResumeService
logger = logging.getLogger(__name__)

def get_related_species(request, query):

    query = unquote(query).strip()  

    related_species = Species.objects.filter(
        Q(scientific_name__iexact=query) | Q(hosts__icontains=query)
    ).distinct()

    if not related_species.exists():
        return JsonResponse({"error": "No se encontraron especies relacionadas"}, status=404)

    species_list = [
        {
            "id": species.id,
            "scientific_name": species.scientific_name,
            "common_names": species.common_names,
            "synonyms": species.synonyms,
            "invasiveness_description": species.invasiveness_description,
            "distribution": species.distribution,
            "impact": species.impact,
            "habitat": species.habitat,
            "life_cycle": species.life_cycle,
            "reproduction": species.reproduction,
            "hosts": species.hosts,
            "symptoms": species.symptoms,
            "affected_organs": species.affected_organs,
            "environmental_conditions": species.environmental_conditions,
            "prevention_control": species.prevention_control,
            "uses": species.uses,
            "source_url": species.source_url,
        }
        for species in related_species
    ]

    return JsonResponse({"related_species": species_list})

def get_plague_news(request, cabi_id):
    try:
        species = CabiSpecies.objects.get(id=cabi_id)

        related_news = SpeciesNews.objects.filter(scientific_name=species.scientific_name)

        news_data = SpeciesNewsSerializer(related_news, many=True).data

        return JsonResponse(news_data, safe=False)

    except CabiSpecies.DoesNotExist:
        return JsonResponse({"error": "CabiSpecies no encontrado"}, status=404)
def get_plague_summary_view(request, cabi_id):

    scraper_info = ResumeService.get_plague_summary(cabi_id)

    if scraper_info is None:
        return JsonResponse({"error": "CabiSpecies no encontrado"}, status=404)

    return JsonResponse(scraper_info, safe=False)
class Pagination(PageNumberPagination):
    page_size = 10 
    page_size_query_param = 'page_size' 
    max_page_size = 100 
class ScraperURLViewSet(viewsets.ModelViewSet):
    queryset = ScraperURL.objects.all().distinct().order_by("id")
    serializer_class = ScraperURLSerializer
    pagination_class = Pagination


class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Species.objects.select_related("scraper_source").distinct().order_by("-created_at")
    serializer_class = SpeciesSerializer
    pagination_class = Pagination


class SpeciesCABIViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CabiSpecies.objects.select_related("scraper_source").distinct().order_by("-created_at")
    serializer_class = SpeciesCabiSerializer
    pagination_class = Pagination



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
        user_id = self.request.query_params.get("user_id")

        if user_id:
            if not self.request.user.is_staff:  
                raise PermissionDenied("No tienes permisos para ver otras suscripciones.")
            return SpeciesSubscription.objects.filter(user_id=user_id).order_by("-created_at")

        return SpeciesSubscription.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            subscription = serializer.save(user=request.user)  # Asigna el usuario autenticado

            self.send_subscription_email(subscription)

            return Response(
                {"message": "Suscripción guardada exitosamente", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"error": "Error al guardar la suscripción", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        instance = get_object_or_404(SpeciesSubscription, id=kwargs["pk"], user=request.user)
        self.perform_destroy(instance)

        return Response(
            {"message": "Suscripción eliminada correctamente"},
            status=status.HTTP_204_NO_CONTENT,
        )

    def send_subscription_email(self, subscription):
        user = subscription.user
        scientific_name = subscription.scientific_name

        subject = "✅ Confirmación de suscripción a especies"
        html_content = f"""
            <p>Hola {user.first_name},</p>
            <p>Te has suscrito con éxito a notificaciones sobre la especie:</p>
            <p><b>🔬 Nombre Científico: {scientific_name}</b></p>
            <p>Te notificaremos cuando haya nuevas noticias relacionadas.</p>
            <p>¡Gracias por usar nuestra plataforma!</p>
        """

        logger.info(f"📩 Enviando confirmación de suscripción a {user.email}")
        EmailService.send_email(subject, [user.email], html_content)