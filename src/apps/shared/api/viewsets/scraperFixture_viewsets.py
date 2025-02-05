from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from ...models.scraperURL import ScraperURL
from ...utils.scrapers import (
    scraper_iucngisd,
    scraper_coleoptera_neotropical,
    scraper_e_floras,
    scraper_ansci_cornell,
    scraper_flora_harvard,
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
    scraper_flora_habitas,
    scraper_cdfa,
    scraper_nal_usda,
    scraper_ers_usda,
    scraper_ars_usda,
    scraper_hort_purdue,
    scraper_cdfa,
    scraper_ippc_int,
    scraper_sciencedirect,
    scraper_agriculture_gov,
    scraper_cabi_library,
    scraper_ecoport,
    scraper_pestnet
)

SCRAPER_FUNCTIONS = {
    1: scraper_iucngisd,
    2: scraper_coleoptera_neotropical,
    3: scraper_e_floras,
    4: scraper_ansci_cornell,
    5: scraper_flora_harvard,
    6: scraper_aphidnet,
    7: scraper_pdf,
    8: scraper_aguiar_hvr,
    9: scraper_gene_affrc,
    10: scraper_plant_ifas,
    11: scraper_plant_atlas,
    12: scraper_flmnh_ufl,
    13: scraper_iucnredlist,
    14: scraper_ala_org,
    15: scraper_pnw_hand_books,
    16: scraper_ipm_illinoes,
    17: scraper_pest_alerts,
    18: scraper_cabi_digital,
    19: scraper_ndrs_org,
    20: scraper_ippc,
    21: scraper_eppo,
    22: scraper_se_eppc,
    23: scraper_mycobank_org,
    24: scraper_nematode,
    25: scraper_diaspididae,
    26: scraper_genome_jp,
    27: scraper_plants_usda_gov,
    28: scraper_fws_gov,
    29: scraper_fao_org,
    30: scraper_index_fungorum,
    31: scraper_nemaplex_plant_host,
    32: scraper_aphis_usda,
    33: scraper_eppo_quarentine,
    34: scraper_extento,
    35: scraper_ncbi,
    36: scraper_bonap,
    37: scraper_google_academic,
    38: scraper_biota_nz,
    39: scraper_catalogue_of_life,
    40: scraper_delta,
    41: scraper_nemaplex,
    42: scraper_bugwood,
    43: scraper_padil,
    44: scraper_cal_ipc,
    45: scraper_method_books,
    46: scraper_herbarium,
    47: scraper_agriculture,
    48:scraper_flora_habitas,
    49: scraper_cdfa,
    50: scraper_hort_purdue,
    51: scraper_nal_usda,
    52: scraper_ers_usda,
    53: scraper_ars_usda,
    54: scraper_ippc_int,
    55: scraper_agriculture_gov,
    56: scraper_sciencedirect,
    57: scraper_cabi_library,
    58: scraper_ecoport,
    59: scraper_pestnet
}

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

        mode_scrapeo = scraper_url.mode_scrapeo
        scraper_function = SCRAPER_FUNCTIONS.get(mode_scrapeo)
        
        if not scraper_function:
            return Response(
                {"error": "Modo de scrapeo no reconocido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract parameters
        kwargs = {
            "url": url,
            "sobrenombre": scraper_url.sobrenombre
        }

        try:
            response = scraper_function(**kwargs)

            scraper_url.fecha_scraper = datetime.now()
            scraper_url.save()

            return response

        except Exception as e:
            return Response(
                {"error": f"Error durante el scrapeo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
