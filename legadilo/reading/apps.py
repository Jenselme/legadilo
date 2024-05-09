from django.apps import AppConfig


class ReadingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legadilo.reading"

    def ready(self):
        import legadilo.reading.signals  # noqa: F401,PLC0415
