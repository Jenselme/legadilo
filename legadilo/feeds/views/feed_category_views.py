#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from legadilo.feeds.models import FeedCategory
from legadilo.users.user_types import AuthenticatedHttpRequest
from legadilo.users.view_decorators import require_cookie_login_or_api_auth


@require_GET
@require_cookie_login_or_api_auth
def feed_categories_autocomplete_view(request: AuthenticatedHttpRequest):
    query = request.GET.get("query", "")
    if not query:
        return JsonResponse([], safe=False)

    choices = FeedCategory.objects.get_choices(request.user, query)
    autocomplete_groups = [{"value": choice[0], "label": choice[1]} for choice in choices]
    return JsonResponse(autocomplete_groups, safe=False)
