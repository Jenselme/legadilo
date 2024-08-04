# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
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

from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from .user import User

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta
else:
    TypedModelMeta = object


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")

    default_reading_time = models.PositiveIntegerField(
        default=200,
        help_text=_(
            "Number of words you read in minutes. Used to calculate the reading time of articles."
        ),
    )

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint("user", name="%(app_label)s_%(class)s_unique_per_user"),
        ]

    def __str__(self):
        return f"UserSettings(user={self.user})"
