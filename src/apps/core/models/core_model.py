
from django.utils import timezone
from django.db import models
from src.apps.core.managers import CoreManager


class CoreModel(models.Model):
    objects: CoreManager = CoreManager()
    all_objects = CoreManager(with_trashed=True, only_trashed=False)
    trashed_objects = CoreManager(only_trashed=True, with_trashed=False)

    id = models.BigAutoField(verbose_name="ID", primary_key=True, auto_created=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(
        blank=True, null=True, db_index=True, editable=False
    )

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()

    def force_delete(self, using=None, keep_parents=False):
        super(CoreModel, self).delete(using=using, keep_parents=keep_parents)

    def is_trashed(self):
        """Checks if this record were soft deleted"""
        return self.deleted_at is not None

    def restore(self):
        """Un deletes a soft deleted record"""
        self.deleted_at = None
        return self.save()

    def clone(self):
        self.id = None
        self.pk = None
        self.created_at = None
        self.updated_at = None
        self.deleted_at = None
        self.save()

    class Meta:
        abstract = True
