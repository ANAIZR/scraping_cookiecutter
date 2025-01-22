from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from src.apps.shared.utils.tasks import scraper_url_task

class ScraperAPIView(APIView):
    def post(self, request):
        url = request.data.get("url")
        if not url:
            return Response(
                {"error": "Se requiere el campo 'url'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scraper_url_task.delay(url)

        return Response(
            {"status": "Tarea de scraping encolada exitosamente"},
            status=status.HTTP_202_ACCEPTED,
        )
