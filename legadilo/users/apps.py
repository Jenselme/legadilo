import contextlib

from allauth.account.signals import user_signed_up
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "legadilo.users"
    verbose_name = _("Users")

    def ready(self):
        with contextlib.suppress(ImportError):
            from legadilo.users.signals import (  # noqa: PLC0415 `import` should be at the top-level of a file
                create_user_settings_on_user_registration,
            )

            user_signed_up.connect(create_user_settings_on_user_registration)
