from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("scraping_cookiecutter")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks(["src.apps.shared.utils", "src.apps.users.utils"])


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))

app.conf.beat_schedule = {
    "scrape-expired-urls-weekly": {
        "task": "src.apps.shared.utils.tasks.scraper_expired_urls_task",  
        "schedule": crontab(hour=8, minute=3, day_of_week=1),  
    }
}


