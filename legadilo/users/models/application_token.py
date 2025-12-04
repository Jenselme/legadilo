# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import secrets
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from legadilo.core.utils.time_utils import utcnow

from .user import User

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta
else:
    TypedModelMeta = object


class ApplicationTokenQuerySet(models.QuerySet["ApplicationToken"]):
    def only_valid(self):
        return self.filter(models.Q(validity_end=None) | models.Q(validity_end__gt=utcnow()))


class ApplicationTokenManager(models.Manager["ApplicationToken"]):
    _hints: dict

    def get_queryset(self):
        return ApplicationTokenQuerySet(model=self.model, using=self._db, hints=self._hints).defer(
            "token"
        )

    @transaction.atomic
    def create_new_token(
        self, user: User, title: str, validity_end: datetime | None = None
    ) -> tuple[ApplicationToken, str]:
        token = secrets.token_urlsafe(settings.TOKEN_LENGTH)
        hashed_token = make_password(token)

        return self.create(
            title=title,
            token=hashed_token,
            validity_end=validity_end,
            user=user,
        ), token

    def use_application_token(
        self, user_email: str, token_uuid: UUID, token_secret: str
    ) -> ApplicationToken | None:
        qs = (
            self.get_queryset()
            .only_valid()
            .defer(None)
            .filter(user__email=user_email, user__is_active=True, uuid=token_uuid)
        )
        qs.update(last_used_at=utcnow())
        application_token = qs.first()
        hashed_token = application_token.token if application_token else "failed-to-find-token"

        if check_password(token_secret, hashed_token):
            return application_token

        return None


class ApplicationToken(models.Model):
    uuid = models.UUIDField(default=uuid4)
    title = models.CharField(
        max_length=255, help_text=_("Give the token a nice name to identify its usage more easily.")
    )
    token = models.CharField(max_length=255)
    validity_end = models.DateTimeField(
        verbose_name=_("Validity end"),
        help_text=_("Leave empty to have a token that will last until deletion."),
        null=True,
        blank=True,
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this token was last used to create an access token."),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(
        "users.User", related_name="application_tokens", on_delete=models.CASCADE
    )

    objects = ApplicationTokenManager()

    class Meta(TypedModelMeta):
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(fields=["token"], name="%(app_label)s_%(class)s_token_unique"),
            models.UniqueConstraint(fields=["uuid"], name="%(app_label)s_%(class)s_uuid_unique"),
            models.UniqueConstraint(
                fields=["title", "user"], name="%(app_label)s_%(class)s_title_user_unique"
            ),
        ]

    def __str__(self):
        return f"ApplicationToken(id={self.id}, user_id={self.user_id}, title={self.title})"

    @property
    def is_valid(self) -> bool:
        return self.validity_end is None or self.validity_end > utcnow()
