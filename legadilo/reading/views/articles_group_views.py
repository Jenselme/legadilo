#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET

from legadilo.reading.models import ArticlesGroup
from legadilo.users.user_types import AuthenticatedHttpRequest


@require_GET
@login_required
def articles_group_details_view(
    request: AuthenticatedHttpRequest, group_id: int, group_slug: str
) -> TemplateResponse:
    return TemplateResponse(request, "reading/articles_group_details.html")


@require_GET
@login_required
def articles_groups_list_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    searched_text = request.GET.get("q", "")
    groups_qs = ArticlesGroup.objects.list_for_admin(request.user, searched_text)

    return TemplateResponse(
        request,
        "reading/articles_groups_list.html",
        {
            "groups": groups_qs,
            "searched_text": searched_text,
        },
    )
