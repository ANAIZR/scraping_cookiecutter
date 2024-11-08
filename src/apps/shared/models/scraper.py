from django.utils import timezone
from django.db import models

from ...core.models import CoreModel

class ScraperURL(CoreModel):
    TYPE_CHOICES = [
        (1, "Web"),
        (2, "Libro"),
    ]
    url = models.URLField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    type_file = models.PositiveSmallIntegerField(choices=TYPE_CHOICES, default=1)
    deleted_at = models.DateTimeField(
        blank=True, null=True, db_index=True, editable=False
    )
    is_active = models.BooleanField(default=True)
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