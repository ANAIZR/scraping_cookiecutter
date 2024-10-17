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

    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(
        blank=True, null=True, db_index=True, editable=False
    )
    is_active = models.BooleanField( default=True)
    username = None
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["password", "is_active"]

    class Meta:
        db_table = "auth_user"
