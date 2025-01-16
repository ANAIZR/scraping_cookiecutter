from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab  # Para definir tareas programadas
from celery import chain

# Configurar el entorno de Django para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('scraping_cookiecutter')

# Usar configuración desde Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Registrar automáticamente las tareas definidas en las apps
app.autodiscover_tasks(['src.apps.shared.models', 'src.apps.users'])

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

# Configurar programación de tareas con Celery Beat
app.conf.beat_schedule = {
    'scrape-and-renew-chain': {
        'task': 'celery.chain',
        'schedule': crontab(hour=23, minute=55),  # Comienza con login a las 23:55 y continúa con el scrapeo
        'args': [['src.apps.users.tasks.renew_access_token', 'src.apps.shared.tasks.scrape_url']],
    },
}
