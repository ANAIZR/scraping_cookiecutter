from django.utils import timezone
from datetime import timedelta
from ...core.models import CoreModel
from django.db import models

from src.apps.users.models import User

class ScraperURL(CoreModel):
    TYPE_CHOICES = [
        (1, "Web"),
        (2, "PDF"),
    ]
    TIME_CHOICES = [(1, "Mensual"), (2, "Trimestral"), (3, "Semestral"), (4, "Semanal")]

    url = models.URLField(max_length=500)
    sobrenombre = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    type_file = models.PositiveSmallIntegerField(choices=TYPE_CHOICES, default=1)
    deleted_at = models.DateTimeField(
        blank=True, null=True, db_index=True, editable=False
    )
    time_choices = models.PositiveSmallIntegerField(choices=TIME_CHOICES, default=1)
    is_active = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict)
    mode_scrapeo = models.PositiveSmallIntegerField(default=1, blank=True, null=True)

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("en_progreso", "En Progreso"),
        ("exitoso", "Exitoso"),
        ("fallido", "Fallido"),
    ]

    estado_scrapeo = models.CharField(
        max_length=45, choices=ESTADO_CHOICES, default="pendiente"
    )
    error_scrapeo = models.TextField(blank=True, null=True)
    fecha_scraper = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "scraper_url"

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save()

    def restore(self):
        self.deleted_at = None
        self.is_active = True
        self.save()

    def is_deleted(self):
        return self.deleted_at is not None

    def get_time_limit(self):
        """
        Calcula la fecha límite basada en `fecha_scraper` o `updated_at`.
        """
        reference_date = self.fecha_scraper or self.updated_at

        # Asegura que `reference_date` sea timezone-aware
        if timezone.is_naive(reference_date):
            reference_date = timezone.make_aware(
                reference_date, timezone.get_current_timezone()
            )

        if self.time_choices == 1:  # Mensual
            return reference_date + timedelta(days=30)
        elif self.time_choices == 2:  # Trimestral
            return reference_date + timedelta(days=90)
        elif self.time_choices == 3:  # Semestral
            return reference_date + timedelta(days=180)
        return reference_date

    def is_time_expired(self):
        """
        Verifica si el tiempo límite ha expirado.
        """
        return timezone.now() > self.get_time_limit()

    def save(self, *args, **kwargs):
        self.fecha_scraper = timezone.now()  # Usar timezone.now()
        super().save(*args, **kwargs)


class Species(models.Model):
    scientific_name = models.CharField(max_length=255, null=True, blank=True)
    common_names = models.TextField(blank=True, null=True)
    synonyms = models.TextField(blank=True, null=True)
    invasiveness_description = models.TextField(blank=True, null=True)
    distribution = models.TextField(blank=True, null=True)
    impact = models.JSONField(blank=True, null=True)
    habitat = models.TextField(blank=True, null=True)
    life_cycle = models.TextField(blank=True, null=True)
    reproduction = models.TextField(blank=True, null=True)
    hosts = models.TextField(blank=True, null=True)
    symptoms = models.TextField(blank=True, null=True)
    affected_organs = models.TextField(blank=True, null=True)
    environmental_conditions = models.TextField(blank=True, null=True)
    prevention_control = models.JSONField(blank=True, null=True)
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

class NewSpecies(models.Model):
    scientific_name = models.CharField(max_length=255, null=True, blank=True)
    common_names = models.TextField(blank=True, null=True)  # Valores separados por comas
    synonyms = models.TextField(blank=True, null=True)  # Valores separados por comas
    distribution = models.TextField(blank=True, null=True)  # Valores separados por comas
    hosts = models.TextField(blank=True, null=True)  # Valores separados por comas
    symptoms = models.TextField(blank=True, null=True)  # Valores separados por comas
    affected_organs = models.TextField(blank=True, null=True)  # Valores separados por comas
    uses = models.TextField(blank=True, null=True)  # Valores separados por comas
    prevention_control = models.JSONField(default=dict, blank=True, null=True)  # {"Prevención": "", "Control": ""}
    invasiveness_description = models.TextField(blank=True, null=True)
    impact = models.JSONField(default=dict, blank=True, null=True)  # {"Económico": "", "Ambiental": "", "Social": ""}
    habitat = models.TextField(blank=True, null=True)
    life_cycle = models.TextField(blank=True, null=True)
    reproduction = models.TextField(blank=True, null=True)
    environmental_conditions = models.TextField(blank=True, null=True)
    source_url = models.URLField(max_length=500, unique=True)
    scraper_source = models.ForeignKey(
        "ScraperURL",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_species",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "new_species"

    def __str__(self):
        return self.scientific_name if self.scientific_name else "Unnamed Species"

    def get_list_from_comma_separated(self, field_name):
        """Convierte un campo de texto separado por comas en una lista."""
        value = getattr(self, field_name, "")
        return [item.strip() for item in value.split(",") if item.strip()]

    def get_common_names_list(self):
        return self.get_list_from_comma_separated("common_names")

    def get_synonyms_list(self):
        return self.get_list_from_comma_separated("synonyms")

    def get_distribution_list(self):
        return self.get_list_from_comma_separated("distribution")

    def get_hosts_list(self):
        return self.get_list_from_comma_separated("hosts")

    def get_symptoms_list(self):
        return self.get_list_from_comma_separated("symptoms")

    def get_affected_organs_list(self):
        return self.get_list_from_comma_separated("affected_organs")

    def get_uses_list(self):
        return self.get_list_from_comma_separated("uses")

    def get_prevention_control(self):
        """Retorna el JSON de prevención y control asegurando claves fijas."""
        return self.prevention_control or {"Prevención": "", "Control": ""}
    def get_impact(self):
        """Retorna el JSON de impacto asegurando claves fijas."""
        return self.impact or {"Económico": "", "Ambiental": "", "Social": ""}


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
    scientific_name = models.CharField(max_length=255, blank=True, null=True)
    distribution = models.JSONField(
        blank=True, null=True
    )  
    hosts = models.JSONField(blank=True, null=True)  
    name_subscription = models.CharField(max_length=255, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "scientific_name", "distribution", "hosts")
        db_table = "species_subscription"

    def __str__(self):
        filters = []
        if self.scientific_name:
            filters.append(f"Scientific Name: {self.scientific_name}")
        if self.distribution:
            filters.append(
                f"Distribution: {', '.join(self.distribution)}"
            )  # Convierte JSON a texto
        if self.hosts:
            filters.append(f"Hosts: {', '.join(self.hosts)}")

        filters_text = " | ".join(filters) if filters else "All"
        return f"{self.user.email} -> {filters_text}"
class SpeciesNews(models.Model):
    species = models.ForeignKey(
        "NewSpecies",
        on_delete=models.CASCADE,
        related_name="news",
    )
    distribution = models.TextField(blank=True, null=True)  
    summary = models.TextField() 
    publication_date = models.DateField()  
    source_url = models.URLField(max_length=500, unique=True)  

    class Meta:
        db_table = "species_news"
        ordering = ["-publication_date"]  

    def __str__(self):
        return f"Noticia sobre {self.species.scientific_name} - {self.publication_date}"