from django.db.models import Q
from ..models.species import CabiSpecies, Species
from ..models.urls import ScraperURL

class ResumeService:
    @staticmethod
    def get_plague_summary(cabi_id):

        try:
            cabi_species = CabiSpecies.objects.get(id=cabi_id)

            species_related = Species.objects.filter(
                Q(scientific_name__icontains=cabi_species.scientific_name) |
                Q(common_names__icontains=cabi_species.scientific_name) |
                Q(synonyms__icontains=cabi_species.scientific_name) |
                Q(invasiveness_description__icontains=cabi_species.scientific_name)
            )

            scraper_info = []
            scrapers = ScraperURL.objects.all()

            for scraper in scrapers:
                species_for_scraper = species_related.filter(scraper_source=scraper)

                hosts_list = set(species_for_scraper.exclude(hosts="").values_list('hosts', flat=True))
                distribution_list = set(species_for_scraper.exclude(distribution="").values_list('distribution', flat=True))
                climate_list = set(species_for_scraper.exclude(environmental_conditions="").values_list('environmental_conditions', flat=True))

                def format_list(data_set):
                    return ", ".join(data_set) if data_set else ""

                formatted_hosts = format_list(hosts_list)
                formatted_distribution = format_list(distribution_list)
                formatted_climate = format_list(climate_list)

                description = []
                if formatted_hosts:
                    description.append("se encontró información de hospedantes")
                if formatted_distribution:
                    description.append("se encontró información de distribución")
                if formatted_climate:
                    description.append("se encontró información de variables climáticas")

                description_text = " y ".join(description) if description else "no se encontró ninguna información"

                scraper_info.append({
                    "id": scraper.id,
                    "url": scraper.url,
                    "description": description_text,
                    "hosts": formatted_hosts,
                    "distribution": formatted_distribution,
                    "climatic_variables": formatted_climate,
                })

            return scraper_info

        except CabiSpecies.DoesNotExist:
            return None
