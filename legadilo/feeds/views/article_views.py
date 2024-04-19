from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from legadilo.feeds import constants
from legadilo.feeds.models import Article, ReadingList
from legadilo.feeds.views.feed_views_utils import get_js_cfg_from_reading_list
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.urls import validate_from_url, validate_referer_url


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
            "from_url": _get_from_url_for_article_details(request, request.GET),
        },
    )


def _get_from_url_for_article_details(request, query_dict) -> str:
    return validate_from_url(
        request, query_dict.get("from_url"), reverse("feeds:default_reading_list")
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

    is_read_status_update = constants.UpdateArticleActions.is_read_status_update(update_action)
    from_url = _get_from_url_for_article_details(request, request.POST)
    for_article_details = request.POST.get("for_article_details", "").lower() == "true"

    if for_article_details:
        if is_read_status_update:
            return HttpResponseRedirect(from_url)
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("feeds:default_reading_list"))
        )

    if not request.htmx:
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("feeds:default_reading_list"))
        )

    try:
        displayed_reading_list_id = int(request.POST.get("displayed_reading_list_id"))  # type: ignore[arg-type]
        reading_list = ReadingList.objects.get(id=displayed_reading_list_id)
        js_cfg = get_js_cfg_from_reading_list(reading_list)
    except (ValueError, TypeError, ReadingList.DoesNotExist):
        displayed_reading_list_id = None
        js_cfg = {}

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
            "js_cfg": js_cfg,
            "from_url": from_url,
        },
    )
