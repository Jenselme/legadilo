from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "legadilo.users"
    verbose_name = _("Users")

    def ready(self):
        import legadilo.users.signals  # noqa: F401,PLC0415
