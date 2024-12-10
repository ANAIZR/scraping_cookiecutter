import os
import sys
 
if __name__ == "__main__":
    settings_module = "config.settings.test" if "test" in sys.argv else "config.settings.local"
   
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
 
 
 
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
 
        raise
 
    # Ejecuta el comando desde la línea de comandos de Django
    execute_from_command_line(sys.argv)
 