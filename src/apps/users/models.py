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
        (1, 'Administrador'),
        (2, 'Funcionario'),
    ]

    username = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    system_role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='funcionario'
    )
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(
        blank=True, null=True, db_index=True, editable=False
    )
    is_active = models.BooleanField(default=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "password", "is_active"]

    class Meta:
        db_table = "auth_user"

    def save(self, *args, **kwargs):
        if self.system_role == '1':  
            update_system_role(self)
        else:
            
            self.is_superuser = False
            self.is_staff = False

        super(User, self).save(*args, **kwargs)

def update_system_role(user):
    if user.system_role == '1':  
        user.is_superuser = True
        user.is_staff = True
    else:
        user.is_superuser = False
        user.is_staff = False

    user.save()


