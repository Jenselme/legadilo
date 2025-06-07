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
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            timezone.activate(request.user.tzinfo)
        else:
            timezone.activate(ZoneInfo("UTC"))

        return self.get_response(request)
