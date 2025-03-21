from ..models.species import  Species
from ..models.urls import ScraperURL


class ResumeService:
    @staticmethod
    def get_species_data_by_name(scientific_name):
        species_related = Species.objects.filter(scientific_name__icontains=scientific_name)

        if not species_related.exists():
            return None

        scraper_info = []

        scrapers = ScraperURL.objects.all()

        for scraper in scrapers:
            species_for_scraper = species_related.filter(scraper_source=scraper)

            if not species_for_scraper.exists():
                continue

            for species in species_for_scraper:
                scraper_info.append({
                    "scraper_id": scraper.id,
                    "scraper_url": scraper.url,
                    "source_url": species.source_url,
                    "hosts": species.hosts,
                    "distribution": species.distribution,
                    "environmental_conditions": species.environmental_conditions,
                })

        return scraper_info

