from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET

from legadilo.feeds.models import Article, ReadingList, Tag
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.pagination import get_requested_page
from legadilo.utils.validators import get_page_number_from_request


@require_GET
@login_required
def tag_with_articles_view(request: AuthenticatedHttpRequest, tag_slug: str) -> TemplateResponse:
    displayed_tag = get_object_or_404(
        Tag,
        slug=tag_slug,
        user=request.user,
    )
    requested_page = get_page_number_from_request(request)
    reading_lists = ReadingList.objects.get_all_for_user(request.user)
    count_articles_of_reading_lists = Article.objects.count_articles_of_reading_lists(reading_lists)
    articles_paginator = Article.objects.get_articles_of_tag(displayed_tag)
    articles_page = get_requested_page(articles_paginator, requested_page)

    return TemplateResponse(
        request,
        "feeds/tag_with_articles.html",
        {
            "fluid_content": True,
            "displayed_tag": displayed_tag,
            "reading_lists": reading_lists,
            "count_articles_of_reading_lists": count_articles_of_reading_lists,
            "articles_page": articles_page,
            "articles_paginator": articles_paginator,
        },
    )
