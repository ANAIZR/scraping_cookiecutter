from django.utils import timezone
import logging
from .urls import ScraperURL

from django.db import models
from src.apps.users.models import User

logger = logging.getLogger(__name__)



class CabiSpecies(models.Model):

    scientific_name = models.CharField(max_length=255, null=True, blank=True)
    common_names = models.TextField(blank=True, null=True)
    synonyms = models.TextField(blank=True, null=True)
    invasiveness_description = models.TextField(blank=True, null=True)
    distribution = models.TextField(blank=True, null=True)
    impact = models.JSONField(default=dict,blank=True, null=True)
    habitat = models.TextField(blank=True, null=True)
    life_cycle = models.TextField(blank=True, null=True)
    reproduction = models.TextField(blank=True, null=True)
    hosts = models.TextField(blank=True, null=True)
    symptoms = models.TextField(blank=True, null=True)
    affected_organs = models.TextField(blank=True, null=True)
    environmental_conditions = models.TextField(blank=True, null=True)
    prevention_control = models.JSONField(default=dict,blank=True, null=True)
    uses = models.TextField(blank=True, null=True)
    source_url = models.URLField(max_length=500, unique=True)
    scraper_source = models.ForeignKey(
        "ScraperURL",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cabi_species",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cabi_species"

    def __str__(self):
        return self.scientific_name

class Species(models.Model):
    scientific_name = models.CharField(max_length=255, null=True, blank=True)
    common_names = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    synonyms = models.TextField(blank=True, null=True)
    invasiveness_description = models.TextField(blank=True, null=True)
    distribution = models.TextField(blank=True, null=True)
    impact = models.JSONField(default=dict,blank=True, null=True)
    habitat = models.TextField(blank=True, null=True)
    life_cycle = models.TextField(blank=True, null=True)
    reproduction = models.TextField(blank=True, null=True)
    hosts = models.TextField(blank=True, null=True)
    symptoms = models.TextField(blank=True, null=True)
    affected_organs = models.TextField(blank=True, null=True)
    environmental_conditions = models.TextField(blank=True, null=True)
    prevention_control = models.JSONField(default=dict,blank=True, null=True)
    uses = models.TextField(blank=True, null=True)
    source_url = models.URLField(max_length=500, unique=True)
    scraper_source = models.ForeignKey(
        "ScraperURL",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="species",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "species"

    def __str__(self):
        return self.scientific_name


class ReportComparison(models.Model):
    scraper_source = models.ForeignKey(
        ScraperURL, on_delete=models.CASCADE, related_name="comparisons"
    )
    object_id1 = models.CharField(max_length=50)
    object_id2 = models.CharField(max_length=50)
    comparison_date = models.DateTimeField(auto_now_add=True)
    info_agregada = models.TextField(blank=True, null=True)
    info_eliminada = models.TextField(blank=True, null=True)
    info_modificada = models.TextField(blank=True, null=True)
    estructura_cambio = models.BooleanField(default=False)

    class Meta:
        db_table = "report_comparison"

    def __str__(self):
        return f"Comparación {self.id} - {self.scraper_source.url}"


class SpeciesSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scientific_name = models.CharField(max_length=255, blank=False, null=False)  # Obligatorio
    name_subscription = models.CharField(max_length=255, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "scientific_name")  # Solo se permite una suscripción por usuario y especie
        db_table = "species_subscription"

    def __str__(self):
        return f"{self.user.email} -> Scientific Name: {self.scientific_name}"
    
class SpeciesNews(models.Model):
    scientific_name = models.CharField(max_length=255, blank=True, null=True)  
    distribution = models.TextField(blank=True, null=True)
    summary = models.TextField()
    publication_date = models.DateField(blank=True, null=True)
    source_url = models.URLField(max_length=500, unique=True)

    class Meta:
        db_table = "species_news"
        ordering = ["-publication_date"]

    def __str__(self):
        return f"Noticia sobre {self.scientific_name} - {self.publication_date}"