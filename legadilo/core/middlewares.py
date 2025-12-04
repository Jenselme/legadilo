# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from zoneinfo import ZoneInfo

from django.conf import settings
from django.http import HttpRequest, HttpResponseBase
from django.middleware.csp import ContentSecurityPolicyMiddleware
from django.utils import timezone
from django.utils.csp import CSP, build_policy


class CSPMiddleware(ContentSecurityPolicyMiddleware):
    """Override the default middleware to allow usage of self for script and style on admin pages.

    It's the easiest solution and avoid having to override many templates with the nonce.
    """

    def process_response(self, request: HttpRequest, response: HttpResponseBase):
        if request.path.startswith(f"/{settings.ADMIN_URL}"):
            response.headers[str(CSP.HEADER_ENFORCE)] = build_policy({
                **settings.SECURE_CSP,
                "script-src": (CSP.SELF,),
                "style-src": (CSP.SELF,),
            })

        return super().process_response(request, response)


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
