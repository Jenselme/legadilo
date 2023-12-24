from django.apps import AppConfig
from django.core import checks


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legadilo.core"

    def ready(self) -> None:
        from .checks import check_dev_mode, check_model_names  # noqa: PLC0415

        checks.register(check_model_names)
        checks.register(check_dev_mode)
