#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from django.core.management import call_command

from legadilo.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestUserStats:
    def test_user_stats(self, mocker):
        UserFactory()
        admin_user = UserFactory(is_staff=True, is_superuser=True)

        send_mail_mock = mocker.patch("legadilo.users.management.commands.user_stats.send_mail")

        call_command("user_stats")

        send_mail_mock.assert_called_once_with(
            from_email="Legadilo <noreply@legadilo.eu>",
            message="total_nb_users: 2\n"
            "total_nb_active_users: 2\n"
            "total_nb_active_users_with_validated_emails: 0\n"
            "total_nb_active_users_connected_last_week: 0\n"
            "total_account_created_last_week: 2\n"
            "nb_users_with_active_session: 0\n",
            recipient_list=[admin_user.email],
            subject="[Legadilo] User stats",
        )
