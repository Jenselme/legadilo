#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET


@require_GET
def security_txt_view(request: HttpRequest) -> TemplateResponse:
    release_year = f"20{settings.VERSION.split('.')[0]}"
    release_month = settings.VERSION.split(".")[1].lstrip("0")
    expires = datetime(
        year=int(release_year), month=int(release_month), day=1, tzinfo=UTC
    ) + timedelta(days=300)
    return TemplateResponse(
        request, "website/security.txt", {"expires": expires.isoformat()}, content_type="text/plain"
    )
