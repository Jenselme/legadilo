#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from functools import wraps

from django.core.exceptions import PermissionDenied

from legadilo.users.api import AuthBearer


def require_cookie_login_or_api_auth(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        is_browser_request = hasattr(request, "user") and request.user.is_authenticated
        if is_browser_request:
            return view_func(request, *args, **kwargs)

        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        api_user = AuthBearer().authenticate(request, token)
        if api_user:
            request.user = api_user
            return view_func(request, *args, **kwargs)

        raise PermissionDenied

    return _wrapped_view
