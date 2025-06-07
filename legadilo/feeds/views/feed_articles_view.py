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
