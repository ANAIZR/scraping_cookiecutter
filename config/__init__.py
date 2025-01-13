from __future__ import absolute_import, unicode_literals

# Importa la instancia de Celery para que esté disponible globalmente
from celery import app as celery_app

__all__ = ("celery_app",)
