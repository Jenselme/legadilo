# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from django.db import models

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta
else:
    TypedModelMeta = object


class TimezoneManager(models.Manager):
    def get_default(self):
        return self.get_queryset().get(name="UTC")


class Timezone(models.Model):
    name = models.CharField()

    objects = TimezoneManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint("name", name="%(app_label)s_%(class)s_unique_tz_name"),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Timezone(name={self.name})"

    @property
    def zone_info(self) -> ZoneInfo:
        return ZoneInfo(self.name)
