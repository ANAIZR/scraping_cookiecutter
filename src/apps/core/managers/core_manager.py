from django.db import models
from src.apps.core.querysets import CoreQuerySet

class CoreManager(models.Manager):
    """
    Provides a Manager to handle Query Sets and manage soft deleting
    """

    def __init__(self, *args, **kwargs):
        self.with_trashed = kwargs.pop("with_trashed", False)
        self.only_trashed = kwargs.pop("only_trashed", False)
        super(CoreManager, self).__init__(*args, **kwargs)

    def get_queryset(self):
        if self.only_trashed:
            return CoreQuerySet(self.model).exclude(deleted_at=None)
        if not self.with_trashed:
            return CoreQuerySet(self.model).filter(deleted_at=None)
        return CoreQuerySet(self.model)

    def force_delete(self):
        return self.get_queryset().force_delete()

    def deleted_queryset(self):
        return CoreQuerySet(self.model).exclude(deleted_at__isnull=True)

    def complete_queryset(self):
        return CoreQuerySet(self.model).all()