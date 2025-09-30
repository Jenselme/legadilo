# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from zoneinfo import ZoneInfo

from csp.middleware import CSPMiddleware as DjangoCSPMiddleware
from csp.middleware import PolicyParts
from django.conf import settings
from django.http.request import HttpRequest
from django.http.response import HttpResponseBase
from django.utils import timezone


class CSPMiddleware(DjangoCSPMiddleware):
    """Override the default middleware to allow usage of self for script and style on admin pages.

    It's the easiest solution and avoid having to override many templates with the nonce.
    """

    def get_policy_parts(
        self,
        request: HttpRequest,
        response: HttpResponseBase,
        report_only: bool = False,  # noqa: FBT001,FBT002 Boolean default positional argument in function definition
    ):
        policy_parts = super().get_policy_parts(request, response, report_only=report_only)
        if not request.path.startswith(f"/{settings.ADMIN_URL}"):
            return policy_parts

        base_replace = policy_parts.replace or {}
        replace = {
            **base_replace,
            "script-src": "'self'",
            "style-src": "'self'",
        }
        return PolicyParts(policy_parts.config, policy_parts.update, replace, policy_parts.nonce)


class TimezoneMiddleware:
    """Enables the user timezone for the current request to localize dates and times.

    Fallbacks to UTC if the user is not authenticated.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            timezone.activate(request.user.tzinfo)
        else:
            timezone.activate(ZoneInfo("UTC"))

        return self.get_response(request)
