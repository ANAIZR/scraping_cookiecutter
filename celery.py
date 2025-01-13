from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Configura la variable de entorno para el settings de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("scraping_cookiecutter")

# Carga la configuración de Celery desde los settings de Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descubre tareas automáticamente desde las apps registradas
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
