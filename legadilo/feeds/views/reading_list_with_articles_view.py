from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_GET

from legadilo.feeds.models import Article, ReadingList
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.pagination import get_requested_page
from legadilo.utils.validators import get_page_number_from_request


@require_GET
@login_required
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
        return HttpResponseRedirect(reverse("feeds:default_reading_list"))

    articles_paginator = Article.objects.get_articles_of_reading_list(displayed_reading_list)
    requested_page = get_page_number_from_request(request)
    articles_page = get_requested_page(articles_paginator, requested_page)
    reading_lists = ReadingList.objects.get_all_for_user(request.user)
    count_articles_of_reading_lists = Article.objects.count_articles_of_reading_lists(reading_lists)

    return TemplateResponse(
        request,
        "feeds/reading_list_with_articles.html",
        {
            "fluid_content": True,
            "reading_lists": reading_lists,
            "count_articles_of_reading_lists": count_articles_of_reading_lists,
            "displayed_reading_list": displayed_reading_list,
            "articles_page": articles_page,
            "articles_paginator": articles_paginator,
        },
    )
