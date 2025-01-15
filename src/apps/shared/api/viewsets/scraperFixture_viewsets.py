from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...models.scraperURL import ScraperURL
from django.utils.dateparse import parse_datetime
import requests

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
        sobrenombre = scraper_url.sobrenombre

        try:
            if mode_scrapeo == 1:
                scraper_iucngisd(url, sobrenombre)
            elif mode_scrapeo == 2:
                scraper_coleoptera_neotropical(url, sobrenombre)
            elif mode_scrapeo == 3:
                scraper_e_floras(
                    url,
                    parameters.get("page_principal"),
                    parameters.get("wait_time", 10),
                    sobrenombre,
                    parameters.get("next_page_selector"),
                )
            elif mode_scrapeo == 4:
                scraper_ansci_cornell(url, parameters.get("wait_time", 10), sobrenombre)
            elif mode_scrapeo == 5:
                scraper_first_mode(
                    url,
                    parameters.get("search_button_selector"),
                    parameters.get("tag_name_first"),
                    parameters.get("tag_name_second"),
                    parameters.get("tag_name_third"),
                    parameters.get("attribute"),
                    parameters.get("content_selector"),
                    parameters.get("selector"),
                    parameters.get("page_principal"),
                    sobrenombre,
                )
            elif mode_scrapeo == 6:
                scraper_aphidnet(url, parameters.get("wait_time", 10), sobrenombre)
            elif mode_scrapeo == 7:
                scraper_pdf(
                    url,
                    sobrenombre,
                    start_page=parameters.get("start_page", 1),
                    end_page=parameters.get("end_page"),
                )
            elif mode_scrapeo == 8:
                scraper_aguiar_hvr(url, parameters.get("wait_time", 10), sobrenombre)
            elif mode_scrapeo == 9:
                scraper_gene_affrc(url, sobrenombre)
            elif mode_scrapeo == 10:
                scraper_plant_ifas(url, sobrenombre)
            elif mode_scrapeo == 11:
                scraper_plant_atlas(url, sobrenombre)
            elif mode_scrapeo == 12:
                scraper_flmnh_ufl(url, sobrenombre)
            elif mode_scrapeo == 13:
                scraper_iucnredlist(url, sobrenombre)
            elif mode_scrapeo == 14:
                scraper_ala_org(url, sobrenombre)
            elif mode_scrapeo == 15:
                scraper_pnw_hand_books(url, sobrenombre)
            elif mode_scrapeo == 16:
                scraper_ipm_illinoes(url)
            elif mode_scrapeo == 17:
                scraper_pest_alerts(url, sobrenombre)
            elif mode_scrapeo == 18:
                scraper_cabi_digital(url, sobrenombre)
            elif mode_scrapeo == 19:
                scraper_ndrs_org(url, sobrenombre)
            elif mode_scrapeo == 20:
                scraper_ippc(url, sobrenombre)
            elif mode_scrapeo == 21:
                scraper_eppo(url, sobrenombre)
            elif mode_scrapeo == 22:
                scraper_se_eppc(url, sobrenombre)
            elif mode_scrapeo == 23:
                scraper_mycobank_org(url, sobrenombre)
            elif mode_scrapeo == 24:
                scraper_nematode(url, sobrenombre)
            elif mode_scrapeo == 25:
                scraper_diaspididae(url, sobrenombre)
            elif mode_scrapeo == 26:
                scraper_genome_jp(url, parameters.get("wait_time", 10), sobrenombre)
            elif mode_scrapeo == 27:
                scraper_plants_usda_gov(url, sobrenombre)
            elif mode_scrapeo == 28:
                scraper_fws_gov(url, sobrenombre)
            elif mode_scrapeo == 29:
                scraper_fao_org(url, sobrenombre)
            elif mode_scrapeo == 30:
                scraper_index_fungorum(url, sobrenombre)
            elif mode_scrapeo == 31:
                scraper_nemaplex_plant_host(url, sobrenombre)
            elif mode_scrapeo == 32:
                scraper_aphis_usda(url, sobrenombre)
            elif mode_scrapeo == 33:
                scraper_eppo_quarentine(url, sobrenombre)
            elif mode_scrapeo == 34:
                scraper_extento(url, sobrenombre)
            elif mode_scrapeo == 35:
                scraper_ncbi(url, sobrenombre)
            elif mode_scrapeo == 36:
                scraper_bonap(url, sobrenombre)
            elif mode_scrapeo == 37:
                scraper_google_academic(url, sobrenombre)
            elif mode_scrapeo == 38:
                scraper_biota_nz(url, sobrenombre)
            elif mode_scrapeo == 39:
                scraper_catalogue_of_life(url, sobrenombre)
            elif mode_scrapeo == 40:
                scraper_delta(url, sobrenombre)
            elif mode_scrapeo == 41:
                scraper_nemaplex(url, sobrenombre)
            elif mode_scrapeo == 42:
                scraper_bugwood(url, sobrenombre)
            elif mode_scrapeo == 43:
                scraper_padil(url, sobrenombre)
            elif mode_scrapeo == 44:
                scraper_cal_ipc(url, sobrenombre)
            elif mode_scrapeo == 45:
                scraper_method_books(url, sobrenombre)
            elif mode_scrapeo == 46:
                scraper_herbarium(url, sobrenombre)
            else:
                return Response(
                    {"error": "Modo de scrapeo no reconocido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"error": f"Error durante el scrapeo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
    # Hacer la solicitud a la API de GET con limit=1
            mongo_response = requests.get(
                f"http://127.0.0.1:8000/api/v1/scraper-get-url?url={url}&limit=1"
            )

            mongo_response.raise_for_status()
            mongo_data = mongo_response.json()

            # Validar y analizar Fecha_scraper
            if "data" in mongo_data and len(mongo_data["data"]) > 0:
                raw_fecha_scraper = mongo_data["data"][0].get("Fecha_scraper")
                if raw_fecha_scraper and isinstance(raw_fecha_scraper, str):
                    fecha_scraper = parse_datetime(raw_fecha_scraper)
                else:
                    fecha_scraper = None
            else:
                return Response(
                    {"error": "No se encontraron registros en la API de MongoDB."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Actualizar el campo fecha_scraper si es válido
            if fecha_scraper:
                scraper_url.fecha_scraper = fecha_scraper
                scraper_url.save()

            return Response(
                {"status": "Finalizo correctamente el proceso", "mongo_data": mongo_data},
                status=status.HTTP_200_OK,
            )
        except requests.exceptions.RequestException as e:
            return Response(
                {"error": f"Error al consultar MongoDB: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
