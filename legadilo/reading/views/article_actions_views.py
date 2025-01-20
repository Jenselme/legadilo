# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
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
from http import HTTPStatus
from typing import Any

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
from legadilo.users.user_types import AuthenticatedHttpRequest
from legadilo.utils.urls import validate_referer_url


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
            return redirect_to_reading_list(request)
        return TemplateResponse(
            request,
            "reading/update_article_details_actions.html",
            {
                "article": article,
                "from_url": get_from_url_for_article_details(request, request.POST),
            },
            headers={"HX-Reswap": "none show:none"},
        )

    if not request.htmx:
        return HttpResponseRedirect(
            validate_referer_url(request, reverse("reading:default_reading_list"))
        )

    ctx = get_common_template_context(request, update_action)
    hx_target = f"#{article_card_id(article)}"
    headers = (
        {
            "HX-Reswap": "outerHTML show:none swap:1s",
            "HX-Retarget": hx_target,
        }
        if ctx["delete_article_card"]
        else {"HX-Reswap": "none show:none"}
    )

    return TemplateResponse(
        request,
        "reading/update_article_action.html",
        {**ctx, "articles": [article]},
        headers=headers,
    )


def redirect_to_reading_list(request: AuthenticatedHttpRequest) -> HttpResponse:
    from_url = get_from_url_for_article_details(request, request.POST)
    if not request.htmx:
        return HttpResponseRedirect(from_url)

    return HttpResponse(headers={"HX-Redirect": from_url, "HX-Push-Url": "true"})


def get_common_template_context(
    request: AuthenticatedHttpRequest,
    update_action: constants.UpdateArticleActions,
    *,
    deleting_article: bool = False,
) -> dict[str, Any]:
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
            deleting_article
            or for_later_but_excluded_from_list
            or not_for_later_but_excluded_from_list
        )
    except (ValueError, TypeError, ReadingList.DoesNotExist):
        displayed_reading_list = None
        count_articles_of_current_reading_list = None
        js_cfg = {}
        delete_article_card = False

    reading_lists = ReadingList.objects.get_all_for_user(request.user)
    count_unread_articles_of_reading_lists = Article.objects.count_unread_articles_of_reading_lists(
        request.user, reading_lists
    )

    return {
        "reading_lists": reading_lists,
        "count_unread_articles_of_reading_lists": count_unread_articles_of_reading_lists,
        "displayed_reading_list": displayed_reading_list,
        "js_cfg": js_cfg,
        "from_url": from_url,
        "count_articles_of_current_reading_list": count_articles_of_current_reading_list,
        "delete_article_card": delete_article_card,
    }


@require_POST
@login_required
@transaction.atomic()
def mark_articles_as_read_in_bulk_view(request: AuthenticatedHttpRequest) -> HttpResponse:
    try:
        article_ids = [int(id_) for id_ in request.POST["article_ids"].split(",") if id_]
    except (TypeError, ValueError, KeyError, IndexError):
        article_ids = []

    if len(article_ids) == 0:
        return HttpResponse(
            "You must supply a valid list of ids",
            status=HTTPStatus.BAD_REQUEST,
            content_type="text/plain",
        )

    articles_qs = (
        Article.objects.get_queryset()
        .for_details()
        .filter(user=request.user, id__in=article_ids)
        .order_by("id")
    )
    articles_qs.update_articles_from_action(constants.UpdateArticleActions.MARK_AS_READ)

    return TemplateResponse(
        request,
        "reading/update_article_action.html",
        {
            **get_common_template_context(
                request,
                constants.UpdateArticleActions.MARK_AS_READ,
            ),
            "articles": list(articles_qs),
        },
    )
