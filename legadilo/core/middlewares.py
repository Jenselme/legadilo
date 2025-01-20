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
from zoneinfo import ZoneInfo

from csp.middleware import CSPMiddleware as DjangoCSPMiddleware
from django.conf import settings
from django.utils import timezone


class CSPMiddleware(DjangoCSPMiddleware):
    """Override the default middleware to allow usage of self for script and style on admin pages.

    It's the easiest solution and avoid having to override many templates with the nonce.
    """

    def build_policy(self, request, response):
        if request.path.startswith(f"/{settings.ADMIN_URL}"):
            response._csp_replace = {
                "script-src": "'self'",
                "style-src": "'self'",
            }
        return super().build_policy(request, response)


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            timezone.activate(request.user.tzinfo)
        else:
            timezone.activate(ZoneInfo("UTC"))

        return self.get_response(request)
