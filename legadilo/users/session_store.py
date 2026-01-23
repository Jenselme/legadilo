#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import UTC, datetime
from functools import cached_property

from django.contrib import auth
from django.contrib.sessions.backends.db import SessionStore as DBStore

from legadilo.core.utils.time_utils import utcnow
from legadilo.users.models import UserSession


class SessionStore(DBStore):
    """Inspired by https://github.com/jazzband/django-user-sessions/blob/acc32621a3d9d4c8c1511d98bbac0ddd8bd5f8e6/user_sessions/backends/db.py"""

    _user_id: int | None = None

    @classmethod
    def get_model_class(cls):
        return UserSession

    @cached_property
    def model(self):
        return self.get_model_class()

    def __setitem__(self, key, value):
        if key == auth.SESSION_KEY:
            self._user_id = value
        super().__setitem__(key, value)

    def _get_session_from_db(self):
        s = super()._get_session_from_db()  # type: ignore[misc]
        if s:
            self._user_id = s.user_id
        return s

    # Used in DBStore.save()  # noqa: ERA001 Commented out code
    def create_model_instance(self, data):
        return self.model(
            session_key=self._get_or_create_session_key(),  # type: ignore[attr-defined]
            session_data=self.encode(data),
            expire_date=self.get_expiry_date(),
            user_id=self._user_id,
            created_at=self._get_created_at(data),
            updated_at=utcnow(),
        )

    def _get_created_at(self, data):
        if (
            (account_authentication_methods := data.get("account_authentication_methods"))
            and len(account_authentication_methods) > 0
            and (at := account_authentication_methods[0].get("at"))
        ):
            return datetime.fromtimestamp(at, tz=UTC)

        return utcnow()

    def clear(self):
        super().clear()
        self._user_id = None
