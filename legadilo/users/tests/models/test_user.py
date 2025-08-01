# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from io import StringIO

import pytest
import time_machine
from allauth.account.models import EmailAddress
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError

from legadilo.feeds.tests.factories import FeedFactory
from legadilo.users.models import User
from legadilo.users.tests.factories import UserFactory
from legadilo.utils.time_utils import utcnow


@pytest.mark.django_db
class TestUserQuerySet:
    def test_with_feeds(self, user, other_user):
        FeedFactory(user=user)

        users = list(User.objects.get_queryset().with_feeds(None))

        assert users == [user]

    def test_with_feeds_and_user_ids_limits(self, user, other_user):
        FeedFactory(user=user)
        FeedFactory(user=other_user)

        users = list(User.objects.get_queryset().with_feeds([user.id]))

        assert users == [user]

    def test_invalid_accounts(self):
        with time_machine.travel("2023-01-01"):
            user_to_delete_no_email_address = UserFactory(
                email="user_to_delete_no_email_address@example.com", is_active=False
            )
            user_to_delete_inactive_and_no_verified_email = UserFactory(
                email="user_to_delete_inactive_and_no_verified_email@example.com", is_active=False
            )
            EmailAddress.objects.create(
                user=user_to_delete_inactive_and_no_verified_email,
                email=user_to_delete_inactive_and_no_verified_email.email,
                verified=False,
            )
            user_to_delete_active_and_no_verified_email = UserFactory(
                email="user_to_delete_active_and_no_verified_email@example.com", is_active=True
            )
            EmailAddress.objects.create(
                user=user_to_delete_active_and_no_verified_email,
                email=user_to_delete_active_and_no_verified_email.email,
                verified=False,
            )
            user_to_keep_active_and_verified_email = UserFactory(
                email="user_to_keep_active_and_verified_email@example.com", is_active=True
            )
            EmailAddress.objects.create(
                user=user_to_keep_active_and_verified_email,
                email=user_to_keep_active_and_verified_email.email,
                verified=True,
            )
            user_to_keep_inactive_but_verified_email = UserFactory(
                email="user_to_keep_inactive_but_verified_email@example.com", is_active=False
            )
            EmailAddress.objects.create(
                user=user_to_keep_inactive_but_verified_email,
                email=user_to_keep_inactive_but_verified_email.email,
                verified=True,
            )
        user_to_keep_inactive_no_verified_email_too_recent_for_deletion = UserFactory(
            email="user_to_keep_inactive_no_verified_email_too_recent_for_deletion@example.com",
            is_active=False,
        )
        EmailAddress.objects.create(
            user=user_to_keep_inactive_no_verified_email_too_recent_for_deletion,
            email=user_to_keep_inactive_no_verified_email_too_recent_for_deletion.email,
            verified=False,
        )

        invalid_users = list(User.objects.get_queryset().invalid_accounts().order_by("id"))

        assert invalid_users == [
            user_to_delete_no_email_address,
            user_to_delete_inactive_and_no_verified_email,
            user_to_delete_active_and_no_verified_email,
        ]


@pytest.mark.django_db
class TestUserManager:
    def test_create_user(self):
        user = User.objects.create_user(
            email="john@example.com",
            password="something-r@nd0m!",
        )
        assert user.email == "john@example.com"
        assert not user.is_staff
        assert not user.is_superuser
        assert user.check_password("something-r@nd0m!")
        assert user.username is None

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="something-r@nd0m!",
        )
        assert user.email == "admin@example.com"
        assert user.is_staff
        assert user.is_superuser
        assert user.username is None

    def test_create_superuser_username_ignored(self):
        user = User.objects.create_superuser(
            email="test@example.com",
            password="something-r@nd0m!",
        )
        assert user.username is None

    def test_create_user_invalid_email(self):
        with pytest.raises(ValidationError):
            User.objects.create_user(email="test", password="something-R@nd0m!")

    def test_email_case_insensitive_search(self):
        user = User.objects.create(email="Hacker@example.com")
        user2 = User.objects.get(email="hacker@example.com")
        assert user == user2

    def test_email_case_insensitive_unique(self):
        User.objects.create(email="Hacker@example.com")
        msg = 'duplicate key value violates unique constraint "users_user_email_key"'
        with pytest.raises(IntegrityError, match=msg):
            User.objects.create(email="hacker@example.com")

    def test_cleanup_invalid_users(self):
        with time_machine.travel("2023-01-01"):
            user_to_deleted = UserFactory(email="hacker@example.com", is_active=True)
            EmailAddress.objects.create(
                user=user_to_deleted, email=user_to_deleted.email, verified=False
            )
            user_to_keep = UserFactory(email="other-hacker@example.com", is_active=True)
            EmailAddress.objects.create(user=user_to_keep, email=user_to_keep.email, verified=True)

        deletion_result = User.objects.cleanup_invalid_accounts()

        assert deletion_result == (
            3,
            {"users.UserSettings": 1, "account.EmailAddress": 1, "users.User": 1},
        )
        assert list(User.objects.all()) == [user_to_keep]

    def test_compute_stats(self):
        with time_machine.travel("2023-01-01"):
            UserFactory(is_active=True)

        UserFactory(is_active=False)
        active_user_with_unverified_email = UserFactory(is_active=True)
        EmailAddress.objects.create(
            user=active_user_with_unverified_email,
            email=active_user_with_unverified_email.email,
            verified=False,
        )
        active_user_with_validated_email = UserFactory(is_active=True)
        EmailAddress.objects.create(
            user=active_user_with_validated_email,
            email=active_user_with_validated_email.email,
            verified=True,
        )
        active_user_who_logged_in = UserFactory(is_active=True, last_login=utcnow())
        EmailAddress.objects.create(
            user=active_user_who_logged_in,
            email=active_user_who_logged_in.email,
            verified=True,
        )

        stats = User.objects.compute_stats()

        assert stats == {
            "total_account_created_last_week": 4,
            "total_nb_active_users": 4,
            "total_nb_active_users_connected_last_week": 1,
            "total_nb_active_users_with_validated_emails": 2,
            "total_nb_users": 5,
        }

    def test_list_admin_emails(self):
        admin_user = UserFactory(is_superuser=True, is_staff=True, is_active=True)
        UserFactory(is_superuser=True, is_staff=True, is_active=False)
        UserFactory(is_superuser=False, is_staff=False, is_active=True)

        admin_emails = User.objects.list_admin_emails()

        assert admin_emails == [admin_user.email]


@pytest.mark.django_db
def test_createsuperuser_command():
    """Ensure createsuperuser command works with our custom manager."""
    out = StringIO()
    command_result = call_command(
        "createsuperuser",
        "--email",
        "henry@example.com",
        interactive=False,
        stdout=out,
    )

    assert command_result is None
    assert out.getvalue() == "Superuser created successfully.\n"
    user = User.objects.get(email="henry@example.com")
    assert not user.has_usable_password()


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.pk}/"
