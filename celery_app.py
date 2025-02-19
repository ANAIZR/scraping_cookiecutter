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
    "scrape-url-weekly": {
        "task": "src.apps.shared.utils.tasks.scraper_expired_urls_task",  
        "schedule": crontab(
            hour=1, minute=55, day_of_week=0
        ),  
    },
    "run-mongo-scraper-tuesday-10am": {
        "task": "src.apps.shared.utils.tasks.run_scraper_task",
        "schedule": crontab(hour=5, minute=0, day_of_week=3), 
    },
    "run-compare-reports":{
        "task":"src.apps.shared.utils.tasks.compare_all_scraped_urls_task",
        "schedule":crontab(hour=5, minute=0, day_of_week=4)
    }
}


