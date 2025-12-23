# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later


import typing

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest

from .models import UserSettings

if typing.TYPE_CHECKING:
    from allauth.socialaccount.models import SocialLogin

    from legadilo.users.models import User


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def save_user(self, request, user, form, commit=True):  # noqa: FBT002  boolean default positional argument in function definition
        user = super().save_user(request, user, form, commit)

        UserSettings.objects.create(user=user, timezone=form.cleaned_data["timezone"])

        return user


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: SocialLogin) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def populate_user(
        self, request: HttpRequest, sociallogin: SocialLogin, data: dict[str, typing.Any]
    ) -> User:
        """Populates user information from social provider info.

        See: https://django-allauth.readthedocs.io/en/latest/advanced.html?#creating-and-populating-user-instances
        """
        user = super().populate_user(request, sociallogin, data)
        if not user.name:
            if name := data.get("name"):
                user.name = name
            elif first_name := data.get("first_name"):
                user.name = first_name
                if last_name := data.get("last_name"):
                    user.name += f" {last_name}"
        return user
