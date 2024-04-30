from django.apps import AppConfig


class FeedsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legadilo.feeds"

    def ready(self) -> None:
        import legadilo.feeds.checks  # noqa: PLC0415
        import legadilo.feeds.signals  # noqa: F401,PLC0415
