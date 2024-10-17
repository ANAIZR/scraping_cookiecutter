from django.contrib.auth.models import UserManager
from src.apps.core.querysets import CoreQuerySet


class CoreUserManager(UserManager):
    """
    Provides a Manager to handle Query Sets and manage soft deleting
    """

    def __init__(self, *args, **kwargs):
        self.with_trashed = kwargs.pop("with_trashed", False)
        self.only_trashed = kwargs.pop("only_trashed", False)
        super(CoreUserManager, self).__init__(*args, **kwargs)

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

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user( email, password, **extra_fields)
 
    def create_superuser(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
 
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
 
        return self._create_user( email, password, **extra_fields)