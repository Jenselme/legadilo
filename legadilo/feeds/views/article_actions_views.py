from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from legadilo.feeds import constants
from legadilo.feeds.models import Article, ReadingList
from legadilo.feeds.views.feed_views_utils import get_js_cfg_from_reading_list
from legadilo.feeds.views.view_utils import get_from_url_for_article_details
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.urls import add_query_params, validate_referer_url


@require_POST
@login_required
def delete_article_view(request: AuthenticatedHttpRequest, article_id: int) -> HttpResponse:
    article = get_object_or_404(Article, id=article_id, user=request.user)
    article.delete()

    for_article_details = request.POST.get("for_article_details", "").lower() == "true"
    if for_article_details:
        return _redirect_to_reading_list(request)

    if not request.htmx:
        from_url = get_from_url_for_article_details(request, request.POST)
        return HttpResponseRedirect(from_url)

    return _update_article_card(
        request,
        article,
        hx_reswap="outerHTML show:none swap:1s",
        hx_target=f"#article-card-{article_id}",
    )


def _redirect_to_reading_list(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    from_url = get_from_url_for_article_details(request, request.POST)
    return HttpResponseRedirect(
        add_query_params(from_url, {"full_reload": ["true"]}),
    )


@require_POST
@login_required
def update_article_view(
    request: AuthenticatedHttpRequest,
    article_id: int,
    update_action: constants.UpdateArticleActions,
) -> HttpResponse:
    article = get_object_or_404(
        Article.objects.get_queryset().for_details(), id=article_id, user=request.user
    )
    article.update_article_from_action(update_action)
    article.save()

    is_read_status_update = constants.UpdateArticleActions.is_read_status_update(update_action)
    for_article_details = request.POST.get("for_article_details", "").lower() == "true"

    if for_article_details:
        if is_read_status_update:
            return _redirect_to_reading_list(request)
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("feeds:default_reading_list"))
        )

    if not request.htmx:
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("feeds:default_reading_list"))
        )

    return _update_article_card(
        request, article, hx_reswap="outerHTML show:none", hx_target=f"#article-card-{article.id}"
    )


def _update_article_card(
    request: AuthenticatedHttpRequest, article: Article, *, hx_reswap, hx_target
) -> TemplateResponse:
    from_url = get_from_url_for_article_details(request, request.POST)
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
        headers={
            "HX-Reswap": hx_reswap,
            "HX-Retarget": hx_target,
        },
    )
