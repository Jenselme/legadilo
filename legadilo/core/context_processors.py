# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.conf import settings


def provide_global_context(request):
    return {
        "VERSION": settings.VERSION,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "ACTIVE_VIEW_NAME": request.resolver_match.view_name,
    }
