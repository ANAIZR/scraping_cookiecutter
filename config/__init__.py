from __future__ import absolute_import, unicode_literals

# Esto asegura que Celery se cargue cuando inicias el proyecto Django
from celery_app import app as celery_app

__all__ = ('celery_app',)
