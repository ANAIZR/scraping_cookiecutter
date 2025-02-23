from django.utils import timezone
import logging

from datetime import datetime, timedelta, date, time
from datetime import timedelta
from ...core.models import CoreModel
from django.db import models
from src.apps.users.models import User

logger = logging.getLogger(__name__)


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
        reference_date = self.fecha_scraper or self.updated_at

        if isinstance(reference_date, datetime):
            if timezone.is_naive(reference_date):
                reference_date = timezone.make_aware(
                    reference_date, timezone.get_current_timezone()
                )
        elif isinstance(reference_date, date):
            reference_date = datetime.combine(
                reference_date,
                datetime.min.time(),
                tzinfo=timezone.get_current_timezone(),
            )

        if self.time_choices == 1:
            return reference_date + timedelta(days=30)
        elif self.time_choices == 2:
            return reference_date + timedelta(days=90)
        elif self.time_choices == 3:
            return reference_date + timedelta(days=180)
        elif self.time_choices == 4:
            return reference_date + timedelta(days=7)
        return reference_date

    def is_time_expired(self):
        return timezone.now() > self.get_time_limit()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new or self.is_time_expired():
            from src.apps.shared.utils.tasks import scraper_url_task

            scraper_url_task.apply_async((self.url,), eta=self.get_time_limit())


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
    )  # JSON para manejar múltiples valores
    hosts = models.JSONField(blank=True, null=True)  # JSON para múltiples hosts
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
