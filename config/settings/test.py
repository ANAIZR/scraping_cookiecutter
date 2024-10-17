from .base import *
from .base import TEMPLATES
from .base import env

# GENERAL
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="RHy4UEDieDE9H8L9W4WEKNz9vHUzM0sU7nk5x6pxa2dYxsqinP0Ml0xfOOgXlMfI",
)
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# DEBUGGING FOR TEMPLATES
TEMPLATES[0]["OPTIONS"]["debug"] = True

# MEDIA
MEDIA_URL = "http://media.testserver"