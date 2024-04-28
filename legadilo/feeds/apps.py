from allauth.account.signals import user_signed_up
from django.apps import AppConfig
from django.core import checks


class FeedsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legadilo.feeds"

    def ready(self) -> None:
        from .checks import check_supported_feed_types_are_supported_by_feedparser  # noqa: PLC0415
        from .signals import (  # noqa: PLC0415 `import` should be at the top-level of a file
            create_default_reading_list_on_user_registration,
        )

        checks.register(check_supported_feed_types_are_supported_by_feedparser)
        user_signed_up.connect(create_default_reading_list_on_user_registration)
