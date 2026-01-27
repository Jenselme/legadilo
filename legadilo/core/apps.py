# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from zoneinfo import available_timezones

from django.apps import AppConfig
from django.core import checks
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legadilo.core"

    def ready(self) -> None:
        from .checks import (  # noqa: PLC0415 `import` should be at the top-level of a file
            check_dev_mode,
            check_model_names,
        )

        checks.register(check_model_names)
        checks.register(check_dev_mode)

        post_migrate.connect(self.fill_timezones, sender=self)

    def fill_timezones(self, **kwargs):
        from .models import Timezone  # noqa: PLC0415 `import` should be at the top-level of a file

        timezones = [Timezone(name=tz) for tz in available_timezones()]
        Timezone.objects.bulk_create(timezones, ignore_conflicts=True, unique_fields=["name"])
