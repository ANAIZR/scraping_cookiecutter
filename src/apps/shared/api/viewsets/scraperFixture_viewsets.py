from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...models.scraperURL import ScraperURL
from ..utils.iucngisd import scrape_iucngisd
from ..utils.coleoptera_neotropical import scrape_coleoptera_neotropical
from ..utils.e_floras import scrape_e_floras
from ..utils.ansci_cornell import scrape_ansci_cornell
from ..utils.first_mode import scrape_first_mode
from ..utils.aphidnet import scrape_aphidnet
from ..utils.method_pdf import scrape_pdf
from ..utils.aguiar_hvr import scrape_aguiar_hvr
from ..utils.gene_affrc import scrape_gene_affrc
from ..utils.plant_ifas import scrape_plant_ifas
from ..utils.plant_atlas import scrape_plant_atlas
from ..utils.flmnh_ufl import scrape_flmnh_ufl
from ..utils.iucnredlist import scrape_iucnredlist
from ..utils.ala_org import scrape_ala_org
from ..utils.pnw_hand_books import scrape_pnw_hand_books
from ..utils.ipm_illinois import scrape_ipm_illinoes
from ..utils.pest_alerts import scrape_pest_alerts
from ..utils.cabi_digital import scrape_cabi_digital
from ..utils.ndrs_org import scrape_ndrs_org


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
        wait_time = parameters.get("wait_time", 10)
        sobrenombre = scraper_url.sobrenombre
        tag_name_first = parameters.get("tag_name_first")
        tag_name_second = parameters.get("tag_name_second")
        tag_name_third = parameters.get("tag_name_third")
        tag_name_fourth = parameters.get("tag_name_fourth")
        attribute = parameters.get("attribute")
        attribute_second = parameters.get("attribute_second")
        selector = parameters.get("selector")
        tag_name_third = parameters.get("tag_name_third")
        next_page_selector = parameters.get("next_page_selector")
        start_page = parameters.get("start_page", 1)
        end_page = parameters.get("end_page", None)
        if mode_scrapeo == 1:
            return scrape_iucngisd(
                url,
                wait_time,
                sobrenombre,
            )
        elif mode_scrapeo == 2:
            return scrape_coleoptera_neotropical(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 3:
            return scrape_e_floras(
                url,
                page_principal,
                wait_time,
                sobrenombre,
                next_page_selector,
            )
        elif mode_scrapeo == 4:
            return scrape_ansci_cornell(
                url,
                wait_time,
                sobrenombre,
            )
        elif mode_scrapeo == 5:
            return scrape_first_mode(
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
            return scrape_aphidnet(
                url,
                wait_time,
                sobrenombre,
            )
        elif mode_scrapeo == 7:
            return scrape_pdf(
                url, sobrenombre, start_page=start_page, end_page=end_page
            )
        elif mode_scrapeo == 8:
            return scrape_aguiar_hvr(
                url,
                wait_time,
                sobrenombre,
            )
        elif mode_scrapeo == 9:
            return scrape_gene_affrc(
                url,
                sobrenombre,
                wait_time,
            )
        elif mode_scrapeo == 10:
            return scrape_plant_ifas(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 11:
            return scrape_plant_atlas(
                url,
                sobrenombre,
                
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
        elif mode_scrapeo == 16:
            return scrape_ipm_illinoes(
                url, content_selector, attribute, attribute_second
            )
        elif mode_scrapeo == 17:
            return scrape_pest_alerts(
                url,
                selector,
                content_selector,
                tag_name_first,
                tag_name_second,
                attribute,
                content_selector_second,
                sobrenombre,
            )
        elif mode_scrapeo == 18:
            return scrape_cabi_digital(sobrenombre)
        elif mode_scrapeo == 19:
            return scrape_ndrs_org(sobrenombre)
        return Response(
            {"error": "Modo de scrapeo no reconocido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
