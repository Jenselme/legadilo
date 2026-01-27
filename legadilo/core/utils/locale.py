#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from django.conf import settings
from django.http import HttpResponse
from django.utils import translation


def enforce_language_on_response(response: HttpResponse, language: str | None):
    if not language:
        response.delete_cookie(settings.LANGUAGE_COOKIE_NAME)
        return

    translation.activate(language)
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)


def stop_enforcing_language(response: HttpResponse):
    response.delete_cookie(settings.LANGUAGE_COOKIE_NAME)
