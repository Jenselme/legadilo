# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

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
