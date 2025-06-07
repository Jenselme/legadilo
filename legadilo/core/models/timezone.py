# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
