from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...models.scraperURL import ScraperURL
from ..utils.scrapers.iucngisd import scrape_iucngisd
from ..utils.scrapers.e_floras import scrape_e_floras
from ..utils.scrapers.coleoptera_neotropical import scrape_coleoptera_neotropical
from ..utils.scrapers.ansci_cornell import scrape_ansci_cornell
from ..utils.scrapers.first_mode import scrape_first_mode
from ..utils.scrapers.aphidnet import scrape_aphidnet
from ..utils.scrapers.method_pdf import scrape_pdf
from ..utils.scrapers.aguiar_hvr import scrape_aguiar_hvr
from ..utils.scrapers.gene_affrc import scrape_gene_affrc
from ..utils.scrapers.plant_ifas import scrape_plant_ifas
from ..utils.scrapers.plant_atlas import scrape_plant_atlas
from ..utils.scrapers.flmnh_ufl import scrape_flmnh_ufl
from ..utils.scrapers.iucnredlist import scrape_iucnredlist
from ..utils.scrapers.ala_org import scrape_ala_org
from ..utils.scrapers.pnw_hand_books import scrape_pnw_hand_books
from ..utils.scrapers.ipm_illinois import scrape_ipm_illinoes
from ..utils.scrapers.pest_alerts import scrape_pest_alerts
from ..utils.scrapers.cabi_digital import scrape_cabi_digital
from ..utils.scrapers.ndrs_org import scrape_ndrs_org
from ..utils.scrapers.ippc import scrape_ippc
from ..utils.scrapers.eppo import scrape_eppo
from ..utils.scrapers.se_eppc import scrape_se_eppc
from ..utils.scrapers.mycobank_org import scrape_mycobank_org
from ..utils.scrapers.nematode import scrape_nematode
from ..utils.scrapers.diaspididae import scrape_diaspididae
from ..utils.scrapers.genome_jp import scrape_genome_jp
from ..utils.scrapers.plants_usda_gov import scrape_plants_usda_gov
from ..utils.scrapers.fws_gov import scrape_fws_gov
from ..utils.scrapers.fao_org import scrape_fao_org
from ..utils.scrapers.index_fungorum import scrape_index_fungorum
from ..utils.scrapers.nemaplex_plant_host import scrape_nemaplex_plant_host
from ..utils.scrapers.aphis_usda import scrape_aphis_usda
from ..utils.scrapers.eppo_quarentine import scrape_eppo_quarentine
from ..utils.scrapers.extento import scrape_extento
from ..utils.scrapers.ncbi import scrape_ncbi
from ..utils.scrapers.bonap import scrape_bonap
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
        sobrenombre = scraper_url.sobrenombre
        tag_name_first = parameters.get("tag_name_first")
        tag_name_second = parameters.get("tag_name_second")
        tag_name_third = parameters.get("tag_name_third")
        attribute = parameters.get("attribute")
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
                sobrenombre,
            )
        elif mode_scrapeo == 13:
            return scrape_iucnredlist(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 14:
            return scrape_ala_org(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 15:
            return scrape_pnw_hand_books(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 16:
            return scrape_ipm_illinoes(url)
        elif mode_scrapeo == 17:
            return scrape_pest_alerts(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 18:
            return scrape_cabi_digital(url, sobrenombre)
        elif mode_scrapeo == 19:
            return scrape_ndrs_org(url, sobrenombre)
        elif mode_scrapeo == 20:
            return scrape_ippc(url, sobrenombre)
        elif mode_scrapeo == 21:
            return scrape_eppo(url, sobrenombre)
        elif mode_scrapeo == 22:
            return scrape_se_eppc(url, sobrenombre)
        elif mode_scrapeo == 23:
            return scrape_mycobank_org(url, sobrenombre)
        elif mode_scrapeo == 24:
            return scrape_nematode(url, sobrenombre)
        elif mode_scrapeo == 25:
            return scrape_diaspididae(url, sobrenombre)
        elif mode_scrapeo == 26:
            return scrape_genome_jp(url, wait_time, sobrenombre)
        elif mode_scrapeo == 27:
            return scrape_plants_usda_gov(url, sobrenombre)
        elif mode_scrapeo == 28:
            return scrape_fws_gov(url, sobrenombre)
        elif mode_scrapeo == 29:
            return scrape_fao_org(url, sobrenombre)
        elif mode_scrapeo == 30:
            return scrape_index_fungorum(url, sobrenombre)
        elif mode_scrapeo == 31:
            return scrape_nemaplex_plant_host(url, sobrenombre)
        elif mode_scrapeo == 32:
            return scrape_aphis_usda(url, sobrenombre)
        elif mode_scrapeo == 33:
            return scrape_eppo_quarentine(url, sobrenombre)
        elif mode_scrapeo == 34:
            return scrape_extento(url, sobrenombre)
        elif mode_scrapeo == 35:
            return scrape_ncbi(url, sobrenombre)
        elif mode_scrapeo == 36:
            return scrape_bonap(url, sobrenombre)

        return Response(
            {"error": "Modo de scrapeo no reconocido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
