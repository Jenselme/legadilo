from http import HTTPStatus

from csp.decorators import csp_update
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.feeds.models import Feed
from legadilo.reading.models import Tag
from legadilo.reading.views.list_of_articles_views import (
    UpdateArticlesForm,
    display_list_of_articles,
    update_list_of_articles,
)
from legadilo.users.typing import AuthenticatedHttpRequest


@require_http_methods(["GET", "POST"])
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
    tag_choices = Tag.objects.get_all_choices(request.user)

    status = HTTPStatus.OK
    form = UpdateArticlesForm(tag_choices=tag_choices)
    articles_qs = Feed.objects.get_articles(feed)
    if request.method == "POST":
        status, form = update_list_of_articles(request, articles_qs, tag_choices)

    return display_list_of_articles(
        request,
        articles_qs,
        {
            "page_title": _("Articles of feed '%(feed_title)s'") % {"feed_title": feed.title},
            "displayed_reading_list_id": None,
            "js_cfg": {},
            "update_articles_form": form,
        },
        status=status,
    )
