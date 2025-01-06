from __future__ import absolute_import, unicode_literals
import os
import sys
from celery import Celery

settings_module = os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

app = Celery("scraper_project")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
