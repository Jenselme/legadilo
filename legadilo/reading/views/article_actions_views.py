from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from legadilo.reading import constants
from legadilo.reading.models import Article, ReadingList
from legadilo.reading.templatetags import article_card_id
from legadilo.reading.utils.views import (
    get_from_url_for_article_details,
    get_js_cfg_from_reading_list,
)
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.urls import add_query_params, validate_referer_url


@require_POST
@login_required
def delete_article_view(request: AuthenticatedHttpRequest, article_id: int) -> HttpResponse:
    article = get_object_or_404(Article, id=article_id, user=request.user)
    hx_target = f"#{article_card_id(article)}"
    article.delete()

    for_article_details = request.POST.get("for_article_details", "")
    if for_article_details:
        return _redirect_to_reading_list(request)

    if not request.htmx:
        from_url = get_from_url_for_article_details(request, request.POST)
        return HttpResponseRedirect(from_url)

    return _update_article_card(
        request,
        article,
        hx_reswap="outerHTML show:none swap:1s",
        hx_target=hx_target,
    )


def _redirect_to_reading_list(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    from_url = get_from_url_for_article_details(request, request.POST)
    return HttpResponseRedirect(
        add_query_params(from_url, {"full_reload": ["true"]}),
    )


@require_POST
@login_required
@transaction.atomic()
def update_article_view(
    request: AuthenticatedHttpRequest,
    article_id: int,
    update_action: constants.UpdateArticleActions,
) -> HttpResponse:
    article_qs = (
        Article.objects.get_queryset().for_details().filter(user=request.user, id=article_id)
    )
    article_qs.update_articles_from_action(update_action)
    article = get_object_or_404(article_qs)

    is_read_status_update = constants.UpdateArticleActions.is_read_status_update(update_action)
    for_article_details = request.POST.get("for_article_details", "")

    if for_article_details:
        if is_read_status_update:
            return _redirect_to_reading_list(request)
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("reading:default_reading_list"))
        )

    if not request.htmx:
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("reading:default_reading_list"))
        )

    return _update_article_card(
        request, article, hx_reswap="innerHTML show:none", hx_target=f"#{article_card_id(article)}"
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
    count_unread_articles_of_reading_lists = Article.objects.count_unread_articles_of_reading_lists(
        request.user, reading_lists
    )
    return TemplateResponse(
        request,
        "reading/update_article_action.html",
        {
            "article": article,
            "reading_lists": reading_lists,
            "count_unread_articles_of_reading_lists": count_unread_articles_of_reading_lists,
            "displayed_reading_list_id": displayed_reading_list_id,
            "js_cfg": js_cfg,
            "from_url": from_url,
        },
        headers={
            "HX-Reswap": hx_reswap,
            "HX-Retarget": hx_target,
        },
    )
