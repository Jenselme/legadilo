from typing import Any

from csp.decorators import csp_update
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from legadilo.reading.models import Article, ReadingList, Tag
from legadilo.reading.utils.views import get_js_cfg_from_reading_list
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.pagination import get_requested_page
from legadilo.utils.urls import pop_query_param
from legadilo.utils.validators import get_page_number_from_request


@require_GET
@login_required
@csp_update(IMG_SRC="https:")
def reading_list_with_articles_view(
    request: AuthenticatedHttpRequest, reading_list_slug: str | None = None
):
    try:
        displayed_reading_list = ReadingList.objects.get_reading_list(
            request.user, reading_list_slug
        )
    except ReadingList.DoesNotExist:
        if reading_list_slug is not None:
            return HttpResponseNotFound()
        return HttpResponseRedirect(reverse("reading:default_reading_list"))

    return _display_list_of_articles(
        request,
        Article.objects.get_articles_of_reading_list(displayed_reading_list),
        {
            "page_title": displayed_reading_list.title,
            "displayed_reading_list_id": displayed_reading_list.id,
            "js_cfg": get_js_cfg_from_reading_list(displayed_reading_list),
        },
    )


def _display_list_of_articles(
    request: AuthenticatedHttpRequest, articles_paginator, page_ctx: dict[str, Any]
) -> TemplateResponse:
    # If the full_reload params is passed, we render the full template. To avoid issues with
    # following requests, we must remove it from the URL.
    from_url, full_reload_param = pop_query_param(request.get_full_path(), "full_reload")
    must_do_full_reload = bool(full_reload_param)
    requested_page = get_page_number_from_request(request)
    articles_page = get_requested_page(articles_paginator, requested_page)
    reading_lists = ReadingList.objects.get_all_for_user(request.user)
    count_articles_of_reading_lists = Article.objects.count_articles_of_reading_lists(
        request.user, reading_lists
    )

    response_ctx = {
        **page_ctx,
        "base": {
            "fluid_content": True,
        },
        "reading_lists": reading_lists,
        "count_articles_of_reading_lists": count_articles_of_reading_lists,
        "articles_page": articles_page,
        "next_page_number": articles_page.next_page_number if articles_page.has_next() else None,
        "articles_paginator": articles_paginator,
        "from_url": from_url,
    }
    headers = {"HX-Push-Url": from_url} if must_do_full_reload else {}

    if request.htmx and not must_do_full_reload:
        return TemplateResponse(
            request,
            "reading/partials/article_paginator_page.html",
            response_ctx,
        )

    return TemplateResponse(
        request,
        "reading/list_of_articles.html",
        response_ctx,
        headers=headers,
    )


@require_GET
@login_required
@csp_update(IMG_SRC="https:")
def tag_with_articles_view(request: AuthenticatedHttpRequest, tag_slug: str) -> TemplateResponse:
    displayed_tag = get_object_or_404(
        Tag,
        slug=tag_slug,
        user=request.user,
    )

    return _display_list_of_articles(
        request,
        Article.objects.get_articles_of_tag(displayed_tag),
        {
            "page_title": _("Articles with tag '%(tag_name)s'") % {"tag_name": displayed_tag.title},
            "displayed_reading_list_id": None,
            "js_cfg": {},
        },
    )
