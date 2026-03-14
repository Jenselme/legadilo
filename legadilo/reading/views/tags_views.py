#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from legadilo.reading.models import Tag
from legadilo.users.user_types import AuthenticatedHttpRequest


@require_GET
@login_required
def tags_autocomplete_view(request: AuthenticatedHttpRequest):
    query = request.GET.get("query", "")
    include_hierarchy = request.GET.get("hierarchy", "") != "false"
    if not query:
        return JsonResponse([], safe=False)

    choices, hierarchy = Tag.objects.get_choices_with_hierarchy(request.user, query)
    autocomplete_groups = []
    for choice in choices:
        element = {
            "value": choice[0],
            "label": choice[1],
        }
        if include_hierarchy:
            element["hierarchy"] = hierarchy.get(choice[0], [])  # type: ignore[assignment]

        autocomplete_groups.append(element)

    return JsonResponse(autocomplete_groups, safe=False)
