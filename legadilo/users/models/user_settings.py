# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

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
    timezone = models.ForeignKey(
        "core.Timezone",
        on_delete=models.PROTECT,
        related_name="user_settings",
        help_text=_("Used to display times and updated feeds at a convenient time."),
    )

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint("user", name="%(app_label)s_%(class)s_unique_per_user"),
        ]

    def __str__(self):
        return f"UserSettings(user={self.user})"
