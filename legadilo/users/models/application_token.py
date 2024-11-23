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

from __future__ import annotations

import secrets
from datetime import datetime
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from ...utils.time_utils import utcnow
from .user import User

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta
else:
    TypedModelMeta = object


class ApplicationTokenQuerySet(models.QuerySet["ApplicationToken"]):
    def only_valid(self):
        return self.filter(models.Q(validity_end=None) | models.Q(validity_end__lt=utcnow()))


class ApplicationTokenManager(models.Manager["ApplicationToken"]):
    _hints: dict

    def get_queryset(self):
        return ApplicationTokenQuerySet(model=self.model, using=self._db, hints=self._hints).defer(
            "token"
        )

    def create_new_token(
        self, user: User, title: str, validity_end: datetime | None = None
    ) -> ApplicationToken:
        return self.create(
            title=title,
            token=secrets.token_urlsafe(settings.TOKEN_LENGTH),
            validity_end=validity_end,
            user=user,
        )


class ApplicationToken(models.Model):
    title = models.CharField(max_length=255)
    token = models.CharField(max_length=255)
    validity_end = models.DateTimeField(
        verbose_name=_("Validity end"),
        help_text=_("Leave empty to have a token that will last until deletion."),
        null=True,
        blank=True,
    )
    last_used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(
        "users.User", related_name="application_tokens", on_delete=models.CASCADE
    )

    objects = ApplicationTokenManager()

    class Meta(TypedModelMeta):
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(fields=["token"], name="%(app_label)s_%(class)s_token_unique"),
            models.UniqueConstraint(
                fields=["title", "user"], name="%(app_label)s_%(class)s_title_user_unique"
            ),
        ]

    def __str__(self):
        return f"ApplicationToken(id={self.id}, user_id={self.user_id}, title={self.title})"
