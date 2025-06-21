# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from csp.decorators import csp_update
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.feeds.models import Feed
from legadilo.reading.views.list_of_articles_views import (
    list_or_update_articles,
)
from legadilo.users.user_types import AuthenticatedHttpRequest


@require_http_methods(["GET", "POST"])
@login_required
@csp_update({"img-src": "https:"})  # type: ignore[arg-type]
def feed_articles_view(
    request: AuthenticatedHttpRequest, feed_id: int, feed_slug: str | None = None
) -> TemplateResponse:
    kwargs_to_get_feed = {
        "id": feed_id,
        "user": request.user,
    }
    if feed_slug:
        kwargs_to_get_feed["slug"] = feed_slug
    feed = get_object_or_404(
        Feed,
        **kwargs_to_get_feed,
    )

    return list_or_update_articles(
        request,
        Feed.objects.get_articles(feed),
        _("Articles of feed '%(feed_title)s'") % {"feed_title": feed.title},
        {"linked_with_feeds": [feed.id]},
        extra_ctx={"feed": feed},
    )
