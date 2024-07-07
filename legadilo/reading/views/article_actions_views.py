# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.http import require_POST

from legadilo.reading import constants
from legadilo.reading.models import Article, ReadingList
from legadilo.reading.services.views import (
    get_from_url_for_article_details,
    get_js_cfg_from_reading_list,
)
from legadilo.reading.templatetags import article_card_id
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
        constants.UpdateArticleActions.DO_NOTHING,
        hx_target=hx_target,
        delete_article_card=True,
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
        return _update_article_details_actions(request, article)

    if not request.htmx:
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("reading:default_reading_list"))
        )

    return _update_article_card(
        request,
        article,
        update_action,
        hx_target=f"#{article_card_id(article)}",
        delete_article_card=False,
    )


def _update_article_details_actions(
    request: AuthenticatedHttpRequest, article: Article
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "reading/update_article_details_actions.html",
        {
            "article": article,
            "from_url": get_from_url_for_article_details(request, request.POST),
        },
        headers={"HX-Reswap": "none show:none"},
    )


def _update_article_card(
    request: AuthenticatedHttpRequest,
    article: Article,
    update_action: constants.UpdateArticleActions,
    *,
    hx_target,
    delete_article_card,
) -> TemplateResponse:
    from_url = get_from_url_for_article_details(request, request.POST)
    try:
        displayed_reading_list_id = int(request.POST.get("displayed_reading_list_id"))  # type: ignore[arg-type]
        displayed_reading_list = ReadingList.objects.select_related("user").get(
            id=displayed_reading_list_id
        )
        count_articles_of_current_reading_list = Article.objects.get_articles_of_reading_list(
            displayed_reading_list
        ).count()
        js_cfg = get_js_cfg_from_reading_list(displayed_reading_list)
        for_later_but_excluded_from_list = (
            update_action == constants.UpdateArticleActions.MARK_AS_FOR_LATER
            and displayed_reading_list.for_later_status
            == constants.ForLaterStatus.ONLY_NOT_FOR_LATER
        )
        not_for_later_but_excluded_from_list = (
            update_action == constants.UpdateArticleActions.UNMARK_AS_FOR_LATER
            and displayed_reading_list.for_later_status == constants.ForLaterStatus.ONLY_FOR_LATER
        )
        delete_article_card = (
            delete_article_card
            or for_later_but_excluded_from_list
            or not_for_later_but_excluded_from_list
        )
    except (ValueError, TypeError, ReadingList.DoesNotExist):
        displayed_reading_list = None
        count_articles_of_current_reading_list = None
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
            "displayed_reading_list": displayed_reading_list,
            "js_cfg": js_cfg,
            "from_url": from_url,
            "count_articles_of_current_reading_list": count_articles_of_current_reading_list,
            "delete_article_card": delete_article_card,
        },
        headers={
            "HX-Reswap": "outerHTML show:none swap:1s"
            if delete_article_card
            else "innerHTML show:none",
            "HX-Retarget": hx_target,
        },
    )
