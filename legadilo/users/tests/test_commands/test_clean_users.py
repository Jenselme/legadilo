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

import pytest
import time_machine
from allauth.account.models import EmailAddress
from django.core.management import call_command

from legadilo.users.models import User
from legadilo.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestCleanUsersCommand:
    def test_clean_invalid_accounts(self):
        with time_machine.travel("2023-01-01"):
            user_to_deleted = UserFactory(email="hacker@example.com", is_active=True)
            EmailAddress.objects.create(
                user=user_to_deleted, email=user_to_deleted.email, verified=False
            )
            user_to_keep = UserFactory(email="other-hacker@example.com", is_active=True)
            EmailAddress.objects.create(user=user_to_keep, email=user_to_keep.email, verified=True)

        call_command("clean_users")

        assert list(User.objects.all()) == [user_to_keep]
