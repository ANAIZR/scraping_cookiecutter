from django.db import models
from django.utils import timezone


class CoreQuerySet(models.QuerySet):
    """
    Provides a Query Set to handle soft deleting
    """

    def delete(self):
        """Soft deleting when it's necessary from query sets chains"""
        return super(CoreQuerySet, self).update(deleted_at=timezone.now())

    def force_delete(self):
        """Physical deleting when it's necessary from query sets chains"""
        return super(CoreQuerySet, self).delete()

    def trashed(self):
        """Handle query set to get all soft deleting records"""
        return self.exclude(deleted_at=None)

    def with_trashed(self):
        return