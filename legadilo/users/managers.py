# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Self

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.validators import validate_email
from django.db import models

from legadilo.utils.time_utils import utcnow
from legadilo.utils.types import DeletionResult

from . import constants as users_constants

if TYPE_CHECKING:
    from .models import User
else:
    User = AbstractUser


class UserQuerySet(models.QuerySet):
    def with_feeds(self, user_ids: list[int] | None) -> Self:
        qs = self.filter(feeds__isnull=False)
        if user_ids:
            qs = qs.filter(id__in=user_ids)

        return qs.distinct()

    def invalid_accounts(self):
        # Users are created as active, no point in filtering on the active status here.
        return self.alias(
            nb_verified_emails=models.Count(
                "emailaddress", filter=models.Q(emailaddress__verified=True)
            )
        ).filter(
            date_joined__lt=utcnow() - timedelta(days=users_constants.INVALID_USERS_RETENTION_DAYS),
            nb_verified_emails=0,
        )


class UserManager(DjangoUserManager[User]):
    """Custom manager for the User model."""

    _hints: dict

    def get_queryset(self) -> UserQuerySet:
        return UserQuerySet(self.model, using=self._db, hints=self._hints)

    def _create_user(self, email: str, password: str | None, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        validate_email(email)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[override]
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def get(self, *args, **kwargs):
        return self.select_related("settings", "settings__timezone").get(*args, **kwargs)

    def cleanup_invalid_accounts(self) -> DeletionResult:
        return self.get_queryset().invalid_accounts().delete()

    def compute_stats(self) -> dict[str, int]:
        return self.get_queryset().aggregate(
            total_nb_users=models.Count("id", distinct=True),
            total_nb_active_users=models.Count(
                "id", filter=models.Q(is_active=True), distinct=True
            ),
            total_nb_active_users_connected_last_week=models.Count(
                "id", filter=models.Q(last_login__gt=utcnow() - timedelta(days=7)), distinct=True
            ),
            total_account_created_last_week=models.Count(
                "id", filter=models.Q(date_joined__gt=utcnow() - timedelta(days=7)), distinct=True
            ),
        )

    def list_admin_emails(self) -> list[str]:
        return list(
            self.get_queryset()
            .filter(is_superuser=True, is_staff=True, is_active=True)
            .values_list("email", flat=True)
        )
