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

import httpx


def format_exception(exception: Exception) -> str:
    text = str(exception)
    if text:
        return f"{exception.__class__.__name__}({text})"

    return exception.__class__.__name__


def extract_debug_information(exception: Exception) -> dict | None:
    request: httpx.Request | None = None
    try:
        # Request may not be set or access may raise a RuntimeError. Prevent errors with a try/catch
        if hasattr(exception, "request"):
            request = exception.request
    except RuntimeError:
        pass

    response: httpx.Response | None = None
    if hasattr(exception, "response"):
        response = exception.response

    return {
        "request": {
            "headers": dict(request.headers),
            "url": str(request.url),
            "method": request.method,
        }
        if request
        else None,
        "response": {
            "headers": dict(response.headers),
            "status_code": response.status_code,
            "reason_phrase": response.reason_phrase,
        }
        if response
        else None,
    }
