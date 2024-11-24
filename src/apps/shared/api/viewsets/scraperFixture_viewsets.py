from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...models.scraperURL import ScraperURL
from ..utils.mode_one import scrape_mode_one
from ..utils.mode_two import scrape_mode_two
from ..utils.mode_three import scrape_mode_three
from ..utils.mode_four import scrape_mode_four
from ..utils.mode_five import scrape_mode_five


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
        page_principal = parameters.get("page_principal")
        content_selector = parameters.get("content_selector")
        wait_time = parameters.get("wait_time", 10)
        tag_name = parameters.get("tag_name")
        sobrenombre = scraper_url.sobrenombre
        tag_name_first = parameters.get("tag_name_first")
        tag_name_second = parameters.get("tag_name_second")
        attribute = parameters.get("attribute")
        selector = parameters.get("selector")
        tag_name_third = parameters.get("tag_name_third")
        next_page_selector = parameters.get("next_page_selector")
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
                page_principal,
                wait_time,
                search_button_selector,
                content_selector,
                sobrenombre,
                tag_name_first,
                tag_name_second,
                tag_name_third,
                attribute,
                selector,
                next_page_selector,
            )
        elif mode_scrapeo == 4:
            return scrape_mode_four(
                url,
                search_button_selector,
                selector,
                content_selector,
                tag_name_first,
                tag_name_second,
                attribute,
                wait_time,
                sobrenombre,
            )
        elif mode_scrapeo == 5:
            return scrape_mode_five(
                url,
                search_button_selector,
                tag_name_first,
                tag_name_second,
                tag_name_third,
                attribute,
                content_selector,
                selector,
                page_principal,
                sobrenombre,
            )
        return Response(
            {"error": "Modo de scrapeo no reconocido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
