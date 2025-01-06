import requests
from django.utils import timezone
from django.db import models
from datetime import timedelta

from ...core.models import CoreModel
from apps.shared.tasks import post_to_api_task


class ScraperURL(CoreModel):
    TYPE_CHOICES = [
        (1, "Web"),
        (2, "PDF"),
    ]
    TIME_CHOICES = [(1, "Mensual"), (2, "Trimestral"), (3, "Semestral")]

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
        now = timezone.now()

        if self.time_choices == 1:  # Mensual
            return self.updated_at + timedelta(days=30)
        elif self.time_choices == 2:  # Trimestral
            return self.updated_at + timedelta(days=90)
        elif self.time_choices == 3:  # Semestral
            return self.updated_at + timedelta(days=180)
        return self.updated_at

    def is_time_expired(self):
        return timezone.now() > self.get_time_limit()

    def save(self, *args, **kwargs):
        new_instance = not self.pk
        super().save(*args, **kwargs)
        if new_instance:
            post_to_api_task.delay(self.id)
