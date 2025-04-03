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
from datetime import datetime
from uuid import uuid4

import pytest
import time_machine
from django.db import IntegrityError

from legadilo.users.models import ApplicationToken
from legadilo.users.tests.factories import ApplicationTokenFactory
from legadilo.utils.time_utils import utcdt


@pytest.mark.django_db
class TestApplicationTokenQuerySet:
    def test_only_valid(self, user):
        always_valid_token = ApplicationTokenFactory(
            user=user, validity_end=None, title="Always valid token"
        )
        still_valid_token = ApplicationTokenFactory(
            user=user, validity_end=utcdt(2024, 11, 25), title="Still valid token"
        )
        ApplicationTokenFactory(
            user=user, validity_end=utcdt(2024, 11, 24, 12, 0, 0), title="Expired token"
        )

        with time_machine.travel("2024-11-24 15:00:00"):
            tokens = ApplicationToken.objects.get_queryset().only_valid().order_by("id")

        assert list(tokens) == [always_valid_token, still_valid_token]


@pytest.mark.django_db
class TestApplicationTokenManager:
    def test_create_always_valid_token(self, user):
        application_token, raw_token = ApplicationToken.objects.create_new_token(
            user, "My token", validity_end=None
        )

        assert application_token.title == "My token"
        assert application_token.user == user
        assert application_token.validity_end is None
        assert len(application_token.token) == 59
        # Note: MD5 is only used to hash passwords in tests. We use a true password hashing
        # algorithm in production (and local app)!
        assert application_token.token.startswith("md5$")
        assert len(raw_token) == 67
        assert raw_token != application_token.token

    def test_create_token_with_validity_end(self, user):
        validity_end = utcdt(2024, 11, 24, 12, 0, 0)

        token, _raw_token = ApplicationToken.objects.create_new_token(
            user, "My token", validity_end
        )

        assert token.validity_end == validity_end

    def test_create_tokens_with_same_name(self, user, other_user):
        token_title = ""
        ApplicationToken.objects.create_new_token(user, token_title, validity_end=None)
        ApplicationToken.objects.create_new_token(other_user, token_title, validity_end=None)

        with pytest.raises(IntegrityError):
            ApplicationToken.objects.create_new_token(user, token_title, validity_end=None)


@pytest.mark.django_db
class TestApplicationTokenManagerUseToken:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.application_token, self.token_secret = ApplicationToken.objects.create_new_token(
            user=user, title="My token", validity_end=None
        )

    def test_use_inexistant_token(self, user, django_assert_num_queries):
        with django_assert_num_queries(2):
            found_app_token = ApplicationToken.objects.use_application_token(
                user.email, uuid4(), self.token_secret
            )

        assert found_app_token is None

    def test_use_with_invalid_secret(self, user, django_assert_num_queries):
        with django_assert_num_queries(2):
            found_app_token = ApplicationToken.objects.use_application_token(
                user.email, self.application_token.uuid, "toto"
            )

        assert found_app_token is None

    def test_use_expired(self, user, django_assert_num_queries):
        self.application_token.validity_end = utcdt(2024, 11, 24)
        self.application_token.save()

        with django_assert_num_queries(2):
            found_app_token = ApplicationToken.objects.use_application_token(
                user.email, self.application_token.uuid, self.token_secret
            )

        assert found_app_token is None

    def test_use_with_inactive_user(self, user, django_assert_num_queries):
        user.is_active = False
        user.save()

        with django_assert_num_queries(2):
            found_app_token = ApplicationToken.objects.use_application_token(
                user.email, self.application_token.uuid, self.token_secret
            )

        assert found_app_token is None

    @time_machine.travel("2024-12-01 12:00:00", tick=False)
    def test_use(self, user, django_assert_num_queries):
        with django_assert_num_queries(2):
            found_app_token = ApplicationToken.objects.use_application_token(
                user.email, self.application_token.uuid, self.token_secret
            )

        assert found_app_token is not None
        self.application_token.refresh_from_db()
        assert found_app_token == self.application_token
        assert self.application_token.last_used_at == utcdt(2024, 12, 1, 12, 0, 0)
        assert found_app_token.validity_end is None


class TestApplicationToken:
    @time_machine.travel("2024-11-24 15:00:00")
    @pytest.mark.parametrize(
        ("validity_end", "is_valid"),
        [
            pytest.param(None, True, id="no-validity-end"),
            pytest.param(utcdt(2024, 12, 1), True, id="still-valid"),
            pytest.param(utcdt(2024, 11, 24, 14, 50), False, id="expired"),
        ],
    )
    def test_is_valid(self, validity_end: datetime | None, is_valid: bool):
        token = ApplicationTokenFactory.build(validity_end=validity_end)

        assert token.is_valid == is_valid
