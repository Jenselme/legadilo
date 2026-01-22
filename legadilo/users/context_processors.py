# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.conf import settings

from legadilo.users.constants import USER_SETTINGS_PAGES


def allauth_settings(request):
    """Expose some settings from django-allauth in templates."""
    return {
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
    }


def user_settings(request):
    return {
        "USER_SETTINGS_PAGES": USER_SETTINGS_PAGES,
        "IS_USER_SETTINGS_VIEW": request.resolver_match.view_name in USER_SETTINGS_PAGES,
    }
