from django.apps import AppConfig
from django.core import checks


class FeedsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legadilo.feeds"

    def ready(self) -> None:
        from .checks import check_supported_feed_types_are_supported_by_feedparser  # noqa: PLC0415

        checks.register(check_supported_feed_types_are_supported_by_feedparser)
