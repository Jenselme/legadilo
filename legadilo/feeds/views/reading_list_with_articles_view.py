from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse

from legadilo.feeds.models import Article, ReadingList
from legadilo.users.typing import AuthenticatedHttpRequest


@login_required
def reading_list_with_articles_view(
    request: AuthenticatedHttpRequest, reading_list_slug: str | None = None
):
    try:
        reading_list = ReadingList.objects.get_reading_list(request.user, reading_list_slug)
    except ReadingList.DoesNotExist:
        return HttpResponseRedirect(reverse("feeds:default_reading_list"))

    articles = Article.objects.get_articles_of_reading_list(reading_list)

    return TemplateResponse(
        request,
        "feeds/reading_list_with_articles.html",
        {"reading_list": reading_list, "articles": articles},
    )
