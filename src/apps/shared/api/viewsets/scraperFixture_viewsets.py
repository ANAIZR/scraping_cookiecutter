from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...models.scraperURL import ScraperURL
from datetime import datetime

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
    scraper_delta,
    scraper_nemaplex,
    scraper_bugwood,
    scraper_padil,
    scraper_cal_ipc,
    scraper_method_books,
    scraper_herbarium,
    scraper_agriculture,
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
        next_page_selector = parameters.get("next_page_selector")
        start_page = parameters.get("start_page", 1)
        end_page = parameters.get("end_page", None)

        try:
            if mode_scrapeo == 1:
                response = scraper_iucngisd(url, sobrenombre)
            elif mode_scrapeo == 2:
                response = scraper_coleoptera_neotropical(url, sobrenombre)
            elif mode_scrapeo == 3:
                response = scraper_e_floras(
                    url,
                    page_principal,
                    wait_time,
                    sobrenombre,
                    next_page_selector,
                )
            elif mode_scrapeo == 4:
                response = scraper_ansci_cornell(url, wait_time, sobrenombre)
            elif mode_scrapeo == 5:
                response = scraper_first_mode(
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
                response = scraper_aphidnet(url, wait_time, sobrenombre)
            elif mode_scrapeo == 7:
                response = scraper_pdf(
                    url, sobrenombre, start_page=start_page, end_page=end_page
                )
            elif mode_scrapeo == 8:
                response = scraper_aguiar_hvr(url, wait_time, sobrenombre)
            elif mode_scrapeo == 9:
                response = scraper_gene_affrc(url, sobrenombre)
            elif mode_scrapeo == 10:
                response = scraper_plant_ifas(url, sobrenombre)
            elif mode_scrapeo == 11:
                response = scraper_plant_atlas(url, sobrenombre)
            elif mode_scrapeo == 12:
                response = scraper_flmnh_ufl(url, sobrenombre)
            elif mode_scrapeo == 13:
                response = scraper_iucnredlist(url, sobrenombre)
            elif mode_scrapeo == 14:
                response = scraper_ala_org(url, sobrenombre)
            elif mode_scrapeo == 15:
                response = scraper_pnw_hand_books(url, sobrenombre)
            elif mode_scrapeo == 16:
                response = scraper_ipm_illinoes(url)
            elif mode_scrapeo == 17:
                response = scraper_pest_alerts(url, sobrenombre)
            elif mode_scrapeo == 18:
                response = scraper_cabi_digital(url, sobrenombre)
            elif mode_scrapeo == 19:
                response = scraper_ndrs_org(url, sobrenombre)
            elif mode_scrapeo == 20:
                response = scraper_ippc(url, sobrenombre)
            elif mode_scrapeo == 21:
                response = scraper_eppo(url, sobrenombre)
            elif mode_scrapeo == 22:
                response = scraper_se_eppc(url, sobrenombre)
            elif mode_scrapeo == 23:
                response = scraper_mycobank_org(url, sobrenombre)
            elif mode_scrapeo == 24:
                response = scraper_nematode(url, sobrenombre)
            elif mode_scrapeo == 25:
                response = scraper_diaspididae(url, sobrenombre)
            elif mode_scrapeo == 26:
                response = scraper_genome_jp(url, wait_time, sobrenombre)
            elif mode_scrapeo == 27:
                response = scraper_plants_usda_gov(url, sobrenombre)
            elif mode_scrapeo == 28:
                response = scraper_fws_gov(url, sobrenombre)
            elif mode_scrapeo == 29:
                response = scraper_fao_org(url, sobrenombre)
            elif mode_scrapeo == 30:
                response = scraper_index_fungorum(url, sobrenombre)
            elif mode_scrapeo == 31:
                response = scraper_nemaplex_plant_host(url, sobrenombre)
            elif mode_scrapeo == 32:
                response = scraper_aphis_usda(url, sobrenombre)
            elif mode_scrapeo == 33:
                response = scraper_eppo_quarentine(url, sobrenombre)
            elif mode_scrapeo == 34:
                response = scraper_extento(url, sobrenombre)
            elif mode_scrapeo == 35:
                response = scraper_ncbi(url, sobrenombre)
            elif mode_scrapeo == 36:
                response = scraper_bonap(url, sobrenombre)
            elif mode_scrapeo == 37:
                response = scraper_google_academic(url, sobrenombre)
            elif mode_scrapeo == 38:
                response = scraper_biota_nz(url, sobrenombre)
            elif mode_scrapeo == 39:
                response = scraper_catalogue_of_life(url, sobrenombre)
            elif mode_scrapeo == 40:
                response = scraper_delta(url, sobrenombre)
            elif mode_scrapeo == 41:
                response = scraper_nemaplex(url, sobrenombre)
            elif mode_scrapeo == 42:
                response = scraper_bugwood(url, sobrenombre)
            elif mode_scrapeo == 43:
                response = scraper_padil(url, sobrenombre)
            elif mode_scrapeo == 44:
                response = scraper_cal_ipc(url, sobrenombre)
            elif mode_scrapeo == 45:
                response = scraper_method_books(url, sobrenombre)
            elif mode_scrapeo == 46:
                response = scraper_herbarium(url, sobrenombre)
            elif mode_scrapeo == 47:
                response = scraper_agriculture(url, sobrenombre)
            else:
                return Response(
                    {"error": "Modo de scrapeo no reconocido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            scraper_url.fecha_scraper = datetime.now()
            scraper_url.save()

            return response

        except Exception as e:
            return Response(
                {"error": f"Error durante el scrapeo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
