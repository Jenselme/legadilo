# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from functools import cached_property
from zoneinfo import ZoneInfo

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from legadilo.users.managers import UserManager


class User(AbstractUser):
    """Default custom user model for Legadilo.

    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), db_collation="case_insensitive", unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    # mypy false positive about overriding class variable.
    objects = UserManager()  # type: ignore[misc]

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    @cached_property
    def count_unread_notifications(self) -> int:
        return self.notifications.count_unread(self)

    @cached_property
    def tzinfo(self) -> ZoneInfo:
        return self.settings.timezone.zone_info
