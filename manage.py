import os
import sys

if __name__ == "__main__":
    settings_module = "config.settings.test" if "test" in sys.argv else "config.settings.local"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
