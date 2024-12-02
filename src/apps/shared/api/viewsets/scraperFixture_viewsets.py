from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...models.scraperURL import ScraperURL
from ..utils.first_mode import scrape_first_mode
from ..utils.second_mode import scrape_second_mode
from ..utils.third_mode import scrape_third_mode
from ..utils.fourth_mode import scrape_fourth_mode
from ..utils.fifth_mode import scrape_fifth_mode
from ..utils.sixth_mode import scrape_sixth_mode
from ..utils.seventh_mode import scrape_pdf
from ..utils.eighth_mode import scrape_eighth_mode
from ..utils.ninth_mode import scrape_ninth_mode
from ..utils.tenth_mode import scrape_tenth_mode
from ..utils.eleventh_mode import scrape_eleventh_mode
from ..utils.flmnh_ufl import scrape_flmnh_ufl
from ..utils.iucnredlist import scrape_iucnredlist
from ..utils.ala_org import scrape_ala_org
from ..utils.pnw_hand_books import scrape_pnw_hand_books


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
        search_button_selector_second = parameters.get("search_button_selector_second")
        page_principal = parameters.get("page_principal")
        content_selector = parameters.get("content_selector")
        content_selector_second = parameters.get("content_selector_second")
        content_selector_third = parameters.get("content_selector_third")
        content_selector_fourth = parameters.get("content_selector_fourth")
        content_selector_fifth = parameters.get("content_selector_fifth")
        wait_time = parameters.get("wait_time", 10)
        sobrenombre = scraper_url.sobrenombre
        tag_name_first = parameters.get("tag_name_first")
        tag_name_second = parameters.get("tag_name_second")
        tag_name_third = parameters.get("tag_name_third")
        tag_name_fourth = parameters.get("tag_name_fourth")
        tag_name_fifth = parameters.get("tag_name_fifth")
        tag_name_sixth = parameters.get("tag_name_sixth")
        attribute = parameters.get("attribute")
        attribute_second = parameters.get("attribute_second")
        selector = parameters.get("selector")
        tag_name_third = parameters.get("tag_name_third")
        next_page_selector = parameters.get("next_page_selector")
        title = parameters.get("title")
        start_page = parameters.get("start_page", 1)
        end_page = parameters.get("end_page", None)
        if mode_scrapeo == 1:
            return scrape_first_mode(
                url,
                search_button_selector,
                content_selector,
                tag_name_first,
                wait_time,
                sobrenombre,
            )
        elif mode_scrapeo == 2:
            return scrape_second_mode(
                url,
                sobrenombre,
                content_selector,
            )
        elif mode_scrapeo == 3:
            return scrape_third_mode(
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
            return scrape_fourth_mode(
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
            return scrape_fifth_mode(
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
        elif mode_scrapeo == 6:
            return scrape_sixth_mode(
                url,
                wait_time,
                sobrenombre,
                search_button_selector,
                search_button_selector_second,
                content_selector,
                content_selector_second,
                content_selector_third,
                content_selector_fourth,
                content_selector_fifth,
                tag_name_first,
                tag_name_second,
                tag_name_third,
                tag_name_fourth,
                tag_name_fifth,
                tag_name_sixth,
                attribute,
                title,
            )
        elif mode_scrapeo == 7:
            return scrape_pdf(
                url, sobrenombre, start_page=start_page, end_page=end_page
            )
        elif mode_scrapeo == 8:
            return scrape_eighth_mode(
                url,
                wait_time,
                content_selector,
                selector,
                tag_name_first,
                attribute,
                content_selector_second,
                content_selector_third,
                tag_name_second,
                content_selector_fourth,
                content_selector_fifth,
                attribute_second,
                sobrenombre,
            )
        elif mode_scrapeo == 9:
            return scrape_ninth_mode(
                url,
                selector,
                attribute,
                search_button_selector,
                tag_name_first,
                content_selector,
                content_selector_fourth,
                content_selector_second,
                content_selector_third,
                content_selector_fifth,
                tag_name_second,
                tag_name_third,
                tag_name_fourth,
                sobrenombre,
                wait_time,
            )
        elif mode_scrapeo == 10:
            return scrape_tenth_mode(
                url,
                selector,
                content_selector,
                tag_name_first,
                attribute,
                content_selector_second,
                content_selector_third,
                content_selector_fourth,
                content_selector_fifth,
                sobrenombre,
            )
        elif mode_scrapeo == 11:
            return scrape_eleventh_mode(
                url,
                content_selector_third,
                content_selector_fourth,
                content_selector_fifth,
                tag_name_fourth,
                sobrenombre,
                attribute,
                content_selector,
                content_selector_second,
                selector,
                tag_name_first,
                tag_name_second,
                search_button_selector,
            )
        elif mode_scrapeo == 12:
            return scrape_flmnh_ufl(
                url,
                selector,
                content_selector,
                tag_name_first,
                content_selector_second,
                sobrenombre,
            )
        elif mode_scrapeo == 13:
            return scrape_iucnredlist(
                url,
                selector,
                search_button_selector,
                content_selector,
                content_selector_second,
                attribute,
                tag_name_first,
                tag_name_second,
                tag_name_third,
                tag_name_fourth,
                search_button_selector_second,
                sobrenombre,
            )
        elif mode_scrapeo == 14:
            return scrape_ala_org(
                url,
                search_button_selector,
                tag_name_first,
                selector,
                tag_name_second,
                attribute,
                content_selector,
                tag_name_third,
                sobrenombre,
            )
        elif mode_scrapeo == 15:
            return scrape_pnw_hand_books(
                url,
                selector,
                content_selector,
                attribute,
                tag_name_first,
                tag_name_second,
                search_button_selector,
                sobrenombre,
            )
        return Response(
            {"error": "Modo de scrapeo no reconocido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
