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

from django.http import HttpRequest
from django_htmx.middleware import HtmxDetails

from legadilo.users.models import User


class AuthenticatedHttpRequest(HttpRequest):
    user: User
    htmx: HtmxDetails


class AuthenticatedApiRequest(HttpRequest):
    # In the API, we cannot use user because it's not defined when using auth tokens. We must rely
    # on auth which will always contains the proper user object.
    user: None  # type: ignore[assignment]
    auth: User
