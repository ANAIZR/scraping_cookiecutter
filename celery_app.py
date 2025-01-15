from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab  # Para definir tareas programadas

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
    'scrape-expired-urls': {
        'task': 'src.apps.shared.tasks.scrape_url',
        'schedule': crontab(hour=0, minute=0),  # Ejecutar todos los días a medianoche
    },
    'login-user':{
        'task':'src.apps.users.tasks.renew_access_token',
        'schedule': crontab(hour=23, minute=55),  # Ejecutar todos los
    }
}
