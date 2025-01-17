from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from celery import chain

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("scraping_cookiecutter")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks(["src.apps.shared.models", "src.apps.users"])


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))


app.conf.beat_schedule = {
    "scrape-and-renew-chain": {
        "task": "celery.chain",
        "schedule": crontab(hour=1, minute=55),
        "args": [
            [
                "src.apps.users.tasks.renew_access_token",
                "src.apps.shared.tasks.scrape_url",
            ]
        ],
    },
}
