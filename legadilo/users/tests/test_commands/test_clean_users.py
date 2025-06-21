# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
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
