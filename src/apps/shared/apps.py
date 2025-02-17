from django.apps import AppConfig

class SharedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.shared'

    def ready(self):
        import src.apps.shared.utils.tasks  