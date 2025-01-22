from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from ...models.scraperURL import ScraperURL
from ...utils.tasks import scrape_url_task

class ScraperAPIView(APIView):
    def post(self, request):
        url = request.data.get("url")
        if not url:
            return Response(
                {"error": "Se requiere el campo 'url'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ScraperURL.objects.get(url=url)
        except ScraperURL.DoesNotExist:
            return Response(
                {"error": f"No se encontraron parámetros para la URL: {url}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        task = scrape_url_task.delay(url)

        return Response(
            {
                "status": "Tarea encolada exitosamente",
                "task_id": task.id, 
            },
            status=status.HTTP_202_ACCEPTED,
        )
