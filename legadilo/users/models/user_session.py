#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib.sessions.base_session import AbstractBaseSession, BaseSessionManager
from django.db import models


class UserSessionManager(BaseSessionManager):
    pass


class UserSession(AbstractBaseSession):
    objects = UserSessionManager()  # type: ignore[misc]

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="sessions",
        # Must be nullable: the session is saved first without the user id!
        null=True,
    )

    class Meta(AbstractBaseSession.Meta): ...  # type: ignore[name-defined]

    @classmethod
    def get_session_store_class(cls):
        # Prevent circular import
        from legadilo.users.session_store import SessionStore  # noqa: PLC0415

        return SessionStore
