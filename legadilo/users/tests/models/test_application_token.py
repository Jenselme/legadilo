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
        application_token = ApplicationToken.objects.create_new_token(
            user, "My token", validity_end=None
        )

        assert application_token.title == "My token"
        assert application_token.user == user
        assert application_token.validity_end is None
        assert len(application_token.token) == 67

    def test_create_token_with_validity_end(self, user):
        validity_end = utcdt(2024, 11, 24, 12, 0, 0)

        token = ApplicationToken.objects.create_new_token(user, "My token", validity_end)

        assert token.validity_end == validity_end

    def test_create_tokens_with_same_name(self, user, other_user):
        token_title = ""
        ApplicationToken.objects.create_new_token(user, token_title, validity_end=None)
        ApplicationToken.objects.create_new_token(other_user, token_title, validity_end=None)

        with pytest.raises(IntegrityError):
            ApplicationToken.objects.create_new_token(user, token_title, validity_end=None)
