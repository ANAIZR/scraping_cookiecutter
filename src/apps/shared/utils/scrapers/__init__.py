from .iucngisd import scraper_iucngisd
from .e_floras import scraper_e_floras
from .coleoptera_neotropical import scraper_coleoptera_neotropical
from .ansci_cornell import scraper_ansci_cornell
from .flora_harvard import scraper_flora_harvard
from .aphidnet import scraper_aphidnet
from .method_pdf import scraper_pdf
from .aguiar_hvr import scraper_aguiar_hvr
from .gene_affrc import scraper_gene_affrc
from .plant_ifas import scraper_plant_ifas
from .plant_atlas import scraper_plant_atlas
from .flmnh_ufl import scraper_flmnh_ufl
from .iucnredlist import scraper_iucnredlist
from .ala_org import scraper_ala_org
from .pnw_hand_books import scraper_pnw_hand_books
from .ipm_illinois import scraper_ipm_illinois
from .pest_alerts import scraper_pest_alerts
from .cabi_digital import scraper_cabi_digital
from .ndrs_org import scraper_ndrs_org
from .ippc import scraper_ippc
from .eppo import scraper_eppo
from .se_eppc import scraper_se_eppc
from .mycobank_org import scraper_mycobank_org
from .nematode import scraper_nematode
from .diaspididae import scraper_diaspididae
from .genome_jp import scraper_genome_jp
from .plants_usda_gov import scraper_plants_usda_gov
from .fws_gov import scraper_fws_gov
from .fao_org import scraper_fao_org
from .index_fungorum import scraper_index_fungorum
from .nemaplex_plant_host import scraper_nemaplex_plant_host
from .aphis_usda import scraper_aphis_usda
from .eppo_quarentine import scraper_eppo_quarentine
from .extento import scraper_extento
from .ncbi import scraper_ncbi
from .bonap import scraper_bonap
from .google_academic import scraper_google_academic
from .biota_nz import scraper_biota_nz
from .catalogue_of_life import scraper_catalogue_of_life
from .delta import scraper_delta
from .nemaplex import scraper_nemaplex
from .bugwood import scraper_bugwood
from .padil import scraper_padil
from .cal_ipc import scraper_cal_ipc
from .herbarium import scraper_herbarium
from .fao_agriculture import scraper_agriculture
from .flora_habitas import scraper_flora_habitas
from .cdfa_ca import scraper_cdfa
from .nal_usda import scraper_nal_usda
from .hort_purdue import scraper_hort_purdue
from .ers_usda import scraper_ers_usda
from .ars_usda import scraper_ars_usda
from .agriculture_gov import scraper_agriculture_gov
from .notification_aphis import scraper_notification_aphis
from .fao_org_home import scraper_fao_org_home
from .apsnet import scraper_apsnet
from .gc_ca import scraper_gc_ca
from .sciencedirect import scraper_sciencedirect
from .ippc_int import scraper_ippc_int
from .scientific_discoveries import scraper_scientific_discoveries
from .npdn import scraper_npdn
from .eppo_int import scraper_eppo_int
from .cdnsciencepub import scraper_cdnsciencepub
from .search_usa_gov import scraper_search_usa_gov
from .repository_cimmy import scraper_repository_cimmy
from .agresearchmag import scraper_agresearchmag
from .ippc_int import scraper_ippc_int
from .notification_aphis_usda_gov import scraper_aphis_usda_gov
from .notification_cahfsa import scraper_cahfsa
from .canada_ca import scraper_canada_ca
from .ecoport import scraper_ecoport
from .pestnet import scraper_pestnet
from .scienceopen import scraper_scienceopen
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
    16: scraper_ipm_illinois,
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
    46: scraper_herbarium,
    47: scraper_agriculture,
    48: scraper_flora_habitas,
    49: scraper_cdfa,
    50: scraper_hort_purdue,
    51: scraper_nal_usda,
    52: scraper_ers_usda,
    53: scraper_ars_usda,
    54: scraper_ippc_int,
    55: scraper_agriculture_gov,
    56: scraper_sciencedirect,
    58: scraper_ecoport,
    59: scraper_pestnet,
    60: scraper_fao_org_home,
    61: scraper_scientific_discoveries,
    62: scraper_search_usa_gov,
    63: scraper_apsnet,
    64: scraper_canada_ca,
    65: scraper_npdn,
    66: scraper_eppo_int,
    67: scraper_gc_ca,
    69: scraper_cdnsciencepub,
    70: scraper_scienceopen,
    71: scraper_agresearchmag,
    73: scraper_notification_aphis,
    74: scraper_repository_cimmy,
    75: scraper_ippc_int,
    76: scraper_cahfsa,
    77: scraper_aphis_usda_gov
}
