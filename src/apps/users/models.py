from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from src.apps.core.managers import CoreUserManager


class BaseUserModel(AbstractUser):
    # managers
    objects = CoreUserManager()
    all_objects = CoreUserManager(with_trashed=True, only_trashed=False)
    trashed_objects = CoreUserManager(only_trashed=True, with_trashed=False)

    class Meta:
        abstract = True


class User(BaseUserModel):
    ROLE_CHOICES = [
        (1, "Administrador del sistema"),
        (2, "Funcionario"),
    ]

    username = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    system_role = models.PositiveSmallIntegerField(choices=ROLE_CHOICES, default=2)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(
        blank=True, null=True, db_index=True, editable=False
    )
    is_active = models.BooleanField(default=True)
    access_token = models.CharField(max_length=500, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "password", "is_active"]

    class Meta:
        db_table = "auth_user"

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
