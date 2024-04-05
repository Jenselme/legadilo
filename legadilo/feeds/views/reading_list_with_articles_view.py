from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse

from legadilo.feeds.models import Article, ReadingList
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.validators import get_page_number


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
    requested_page = get_page_number(request)
    articles_page = (
        articles_paginator.page(requested_page)
        if 1 <= requested_page <= articles_paginator.num_pages
        else articles_paginator.page(1)
    )
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
