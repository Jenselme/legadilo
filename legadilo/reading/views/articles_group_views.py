#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET

from legadilo.core.utils.pagination import get_requested_page
from legadilo.core.utils.validators import get_page_number_from_request
from legadilo.reading import constants
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
    groups_paginator = Paginator(
        groups_qs,
        constants.MAX_OBJECTS_PER_PAGE,
        orphans=int(constants.MAX_OBJECTS_PER_PAGE * constants.PAGINATION_ORPHANS_PERCENTAGE),
    )
    requested_page = get_page_number_from_request(request)
    groups_page = get_requested_page(groups_paginator, requested_page)

    return TemplateResponse(
        request,
        "reading/articles_groups_list.html",
        {
            "groups_page": groups_page,
            "groups_paginator": groups_paginator,
            "elided_page_range": groups_paginator.get_elided_page_range(requested_page),
            "searched_text": searched_text,
        },
    )
