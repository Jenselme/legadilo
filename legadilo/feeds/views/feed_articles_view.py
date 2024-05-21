from csp.decorators import csp_update
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from legadilo.feeds.models import Feed
from legadilo.reading.views.list_of_articles_views import display_list_of_articles
from legadilo.users.typing import AuthenticatedHttpRequest


@require_GET
@login_required
@csp_update(IMG_SRC="https:")
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

    return display_list_of_articles(
        request,
        Feed.objects.get_articles(feed),
        {
            "page_title": _("Articles of feed '%(feed_title)s'") % {"feed_title": feed.title},
            "displayed_reading_list_id": None,
            "js_cfg": {},
        },
    )
