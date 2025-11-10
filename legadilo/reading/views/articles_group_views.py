#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from django.template.response import TemplateResponse

from legadilo.users.user_types import AuthenticatedHttpRequest


def articles_group_details_view(
    request: AuthenticatedHttpRequest, group_id: int, group_slug: str
) -> TemplateResponse:
    return TemplateResponse(request, "reading/articles_group_details.html")
