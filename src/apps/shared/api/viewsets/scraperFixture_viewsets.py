from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from src.apps.shared.tasks.scraper_tasks import scraper_url_task
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

        scraper_url = ScraperURL.objects.filter(url=url).first()
        if not scraper_url:
            return Response(
                {"error": f"No se encontraron parámetros para la URL: {url}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            scraper_url_task.apply_async((url,))
        except Exception as e:
            return Response(
                {"error": f"Error al encolar tarea: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"status": "Tarea de scraping encolada exitosamente"},
            status=status.HTTP_202_ACCEPTED,
        )
