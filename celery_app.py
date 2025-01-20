from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("scraping_cookiecutter")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks(["src.apps.shared.models", "src.apps.users"])


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))


app.conf.beat_schedule = {
    "scrape-url-periodic": {
        "task": "src.apps.shared.models.tasks.scrape_url",
        "schedule": crontab(hour=1, minute=55),
    },
}

