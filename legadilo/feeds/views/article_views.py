from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET, require_POST

from legadilo.feeds import constants
from legadilo.feeds.models import Article, ReadingList
from legadilo.users.typing import AuthenticatedHttpRequest


@require_GET
@login_required
def article_details_view(
    request: AuthenticatedHttpRequest, article_id: int, article_slug: str
) -> TemplateResponse:
    article = get_object_or_404(
        Article.objects.get_queryset().for_details(),
        id=article_id,
        slug=article_slug,
        feed__user=request.user,
    )

    return TemplateResponse(
        request,
        "feeds/article_details.html",
        {
            "base": {
                "hide_header": True,
            },
            "article": article,
        },
    )


@require_POST
@login_required
def update_article_view(
    request: AuthenticatedHttpRequest,
    article_id: int,
    update_action: constants.UpdateArticleActions,
) -> HttpResponse:
    article = get_object_or_404(
        Article.objects.get_queryset().for_details(), id=article_id, feed__user=request.user
    )
    article.update_article(update_action)
    article.save()

    if not request.htmx:
        return _redirect_to_origin(request)

    try:
        displayed_reading_list_id = int(request.POST.get("displayed_reading_list_id"))  # type: ignore[arg-type]
    except (ValueError, TypeError):
        displayed_reading_list_id = None

    reading_lists = ReadingList.objects.get_all_for_user(request.user)
    count_articles_of_reading_lists = Article.objects.count_articles_of_reading_lists(reading_lists)
    return TemplateResponse(
        request,
        "feeds/update_article_action.html",
        {
            "article": article,
            "reading_lists": reading_lists,
            "count_articles_of_reading_lists": count_articles_of_reading_lists,
            "displayed_reading_list_id": displayed_reading_list_id,
        },
    )


def _redirect_to_origin(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    referer = request.headers.get("Referer")
    parsed_referer = urlparse(referer)
    redirect_url = request.build_absolute_uri(str(parsed_referer.path))
    if parsed_referer.query:
        redirect_url += "?" + str(parsed_referer.query)
    if parsed_referer.fragment:
        redirect_url += "#" + str(parsed_referer.fragment)
    return HttpResponseRedirect(redirect_url)
