from django.utils import timezone
from datetime import timedelta
from ...core.models import CoreModel
from django.db import models


class ScraperURL(CoreModel):
    TYPE_CHOICES = [
        (1, "Web"),
        (2, "PDF"),
    ]
    TIME_CHOICES = [(1, "Mensual"), (2, "Trimestral"), (3, "Semestral"),(4,"Semanal")]

    url = models.URLField(max_length=500)
    sobrenombre = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    type_file = models.PositiveSmallIntegerField(choices=TYPE_CHOICES, default=1)
    deleted_at = models.DateTimeField(
        blank=True, null=True, db_index=True, editable=False
    )
    fecha_scraper = models.DateTimeField(null=True, blank=True)
    time_choices = models.PositiveSmallIntegerField(choices=TIME_CHOICES, default=1)
    is_active = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict)
    mode_scrapeo = models.PositiveSmallIntegerField(default=1, blank=True, null=True)

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

        if timezone.is_naive(reference_date):
            reference_date = timezone.make_aware(reference_date, timezone.get_current_timezone())

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
            from src.apps.shared.utils.tasks import (
                scraper_url_task,
            )  

            scraper_url_task.apply_async((self.url,), eta=self.get_time_limit())
