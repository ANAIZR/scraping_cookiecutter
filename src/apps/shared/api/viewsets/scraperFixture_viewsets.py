from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...models.scraperURL import ScraperURL
from ..utils.mode_one import scrape_mode_one
from ..utils.mode_two import scrape_mode_two
from ..utils.mode_three import scrape_mode_three


class ScraperAPIView(APIView):
    def post(self, request):

        url = request.data.get("url")
        if not url:
            return Response(
                {"error": "Se requiere el campo 'url'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            scraper_url = ScraperURL.objects.get(url=url)
        except ScraperURL.DoesNotExist:
            return Response(
                {"error": f"No se encontraron parámetros para la URL: {url}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        parameters = scraper_url.parameters
        mode_scrapeo = scraper_url.mode_scrapeo
        search_button_selector = parameters.get("search_button_selector")
        content_selector = parameters.get("content_selector")
        wait_time = parameters.get("wait_time", 10)
        tag_name = parameters.get("tag_name")
        sobrenombre = scraper_url.sobrenombre
        tag_name_one = parameters.get("tag_name_one")
        tag_name_second = parameters.get("tag_name_second")
        attribute = parameters.get("attribute")
        selector = parameters.get("selector")
        tag_name_third = parameters.get("tag_name_third")

        if mode_scrapeo == 1:
            return scrape_mode_one(
                url,
                search_button_selector,
                content_selector,
                tag_name,
                wait_time,
                sobrenombre,
            )

        elif mode_scrapeo == 2:
            return scrape_mode_two(
                url,
                sobrenombre,
                content_selector,
            )
        elif mode_scrapeo == 3:
            return scrape_mode_three(
                url,
                search_button_selector,
                content_selector,
                tag_name_one,
                wait_time,
                sobrenombre,
                tag_name_second,
                attribute,
                selector,
                tag_name_third
            )

        return Response(
            {"error": "Modo de scrapeo no reconocido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
