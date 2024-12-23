from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...models.scraperURL import ScraperURL
from ...utils.scrapers import (
    scraper_iucngisd,
    scraper_e_floras,
    scraper_coleoptera_neotropical,
    scraper_ansci_cornell,
    scraper_first_mode,
    scraper_aphidnet,
    scraper_pdf,
    scraper_aguiar_hvr,
    scraper_gene_affrc,
    scraper_plant_ifas,
    scraper_plant_atlas,
    scraper_flmnh_ufl,
    scraper_iucnredlist,
    scraper_ala_org,
    scraper_pnw_hand_books,
    scraper_ipm_illinoes,
    scraper_pest_alerts,
    scraper_cabi_digital,
    scraper_ndrs_org,
    scraper_ippc,
    scraper_eppo,
    scraper_se_eppc,
    scraper_mycobank_org,
    scraper_nematode,
    scraper_diaspididae,
    scraper_genome_jp,
    scraper_plants_usda_gov,
    scraper_fws_gov,
    scraper_fao_org,
    scraper_index_fungorum,
    scraper_nemaplex_plant_host,
    scraper_aphis_usda,
    scraper_eppo_quarentine,
    scraper_extento,
    scraper_ncbi,
    scraper_bonap,
    scraper_google_academic,
    scraper_biota_nz,
    scraper_catalogue_of_life,
)   


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
            return scraper_iucngisd(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 2:
            return scraper_coleoptera_neotropical(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 3:
            return scraper_e_floras(
                url,
                page_principal,
                wait_time,
                sobrenombre,
                next_page_selector,
            )
        elif mode_scrapeo == 4:
            return scraper_ansci_cornell(
                url,
                wait_time,
                sobrenombre,
            )
        elif mode_scrapeo == 5:
            return scraper_first_mode(
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
            return scraper_aphidnet(
                url,
                wait_time,
                sobrenombre,
            )
        elif mode_scrapeo == 7:
            return scraper_pdf(
                url, sobrenombre, start_page=start_page, end_page=end_page
            )
        elif mode_scrapeo == 8:
            return scraper_aguiar_hvr(
                url,
                wait_time,
                sobrenombre,
            )
        elif mode_scrapeo == 9:
            return scraper_gene_affrc(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 10:
            return scraper_plant_ifas(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 11:
            return scraper_plant_atlas(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 12:
            return scraper_flmnh_ufl(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 13:
            return scraper_iucnredlist(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 14:
            return scraper_ala_org(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 15:
            return scraper_pnw_hand_books(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 16:
            return scraper_ipm_illinoes(url)
        elif mode_scrapeo == 17:
            return scraper_pest_alerts(
                url,
                sobrenombre,
            )
        elif mode_scrapeo == 18:
            return scraper_cabi_digital(url, sobrenombre)
        elif mode_scrapeo == 19:
            return scraper_ndrs_org(url, sobrenombre)
        elif mode_scrapeo == 20:
            return scraper_ippc(url, sobrenombre)
        elif mode_scrapeo == 21:
            return scraper_eppo(url, sobrenombre)
        elif mode_scrapeo == 22:
            return scraper_se_eppc(url, sobrenombre)
        elif mode_scrapeo == 23:
            return scraper_mycobank_org(url, sobrenombre)
        elif mode_scrapeo == 24:
            return scraper_nematode(url, sobrenombre)
        elif mode_scrapeo == 25:
            return scraper_diaspididae(url, sobrenombre)
        elif mode_scrapeo == 26:
            return scraper_genome_jp(url, wait_time, sobrenombre)
        elif mode_scrapeo == 27:
            return scraper_plants_usda_gov(url, sobrenombre)
        elif mode_scrapeo == 28:
            return scraper_fws_gov(url, sobrenombre)
        elif mode_scrapeo == 29:
            return scraper_fao_org(url, sobrenombre)
        elif mode_scrapeo == 30:
            return scraper_index_fungorum(url, sobrenombre)
        elif mode_scrapeo == 31:
            return scraper_nemaplex_plant_host(url, sobrenombre)
        elif mode_scrapeo == 32:
            return scraper_aphis_usda(url, sobrenombre)
        elif mode_scrapeo == 33:
            return scraper_eppo_quarentine(url, sobrenombre)
        elif mode_scrapeo == 34:
            return scraper_extento(url, sobrenombre)
        elif mode_scrapeo == 35:
            return scraper_ncbi(url, sobrenombre)
        elif mode_scrapeo == 36:
            return scraper_bonap(url, sobrenombre)
        elif mode_scrapeo == 37:
            return scraper_google_academic(url, sobrenombre)
        elif mode_scrapeo == 38:
            return scraper_biota_nz(url, sobrenombre)
        elif mode_scrapeo == 39:
            return scraper_catalogue_of_life(url, sobrenombre)

        return Response(
            {"error": "Modo de scrapeo no reconocido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
