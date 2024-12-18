from .base import *
from .base import TEMPLATES
from .base import env

# GENERAL
SECRET_KEY_TOKEN = "RHy4UEDieDE9H8L9W4WEKNz9vHUzM0sU7nk5x6pxa2dYxsqinP0Ml0xfOOgXlMfI"
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default=SECRET_KEY_TOKEN,
)
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# DEBUGGING FOR TEMPLATES
TEMPLATES[0]["OPTIONS"]["debug"] = True

# MEDIA
MEDIA_URL = "http://media.testserver/"

DJANGO_APPS = [
    "src.apps.core",
    "src.apps.shared",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.forms",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "src.apps.users",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
