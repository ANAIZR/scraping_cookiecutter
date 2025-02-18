from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from src.apps.shared.utils.tasks import scraper_url_task
from src.apps.users.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
from src.apps.shared.models.scraperURL import ScraperURL
class ScraperAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        url = request.data.get("url")
        if not url:
            return Response(
                {"error": "Se requiere el campo 'url'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ScraperURL.objects.filter(url=url).exists():  
            return Response(
                {"error": f"No se encontraron parámetros para la URL: {url}"},
                status=status.HTTP_404_NOT_FOUND,  
            )

        scraper_url_task.apply_async((url,))
        return Response(
            {"status": "Tarea de scraping encolada exitosamente"},
            status=status.HTTP_202_ACCEPTED,
        )
