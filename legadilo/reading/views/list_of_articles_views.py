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

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from csp.decorators import csp_update
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods

from legadilo.core.forms import FormChoices
from legadilo.core.forms.fields import MultipleTagsField
from legadilo.core.forms.widgets import MultipleTagsWidget
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag, ReadingList, Tag
from legadilo.reading.models.article import ArticleQuerySet
from legadilo.reading.services.views import get_js_cfg_from_reading_list
from legadilo.reading.templatetags import decode_external_tag
from legadilo.users.user_types import AuthenticatedHttpRequest
from legadilo.utils.pagination import get_requested_page
from legadilo.utils.validators import get_page_number_from_request


@require_GET
@login_required
@csp_update(IMG_SRC="https:")
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
        return HttpResponseRedirect(reverse("reading:default_reading_list"))

    return _display_list_of_articles(
        request,
        Article.objects.get_articles_of_reading_list(displayed_reading_list),
        {
            "page_title": displayed_reading_list.title,
            "displayed_reading_list": displayed_reading_list,
            "js_cfg": get_js_cfg_from_reading_list(displayed_reading_list),
        },
    )


def _display_list_of_articles(
    request: AuthenticatedHttpRequest,
    articles_qs: ArticleQuerySet,
    page_ctx: dict[str, Any],
    *,
    status: HTTPStatus = HTTPStatus.OK,
) -> TemplateResponse:
    articles_per_page = (
        constants.MAX_ARTICLES_PER_PAGE_WITH_READ_ON_SCROLL
        if page_ctx.get("js_cfg", {}).get("is_reading_on_scroll_enabled")
        else constants.MAX_ARTICLES_PER_PAGE
    )
    articles_paginator = Paginator(
        articles_qs,
        articles_per_page,
        # Prevent pages with less that 10% of the number of articles. Display them on the previous
        # page instead of as orphans.
        orphans=int(articles_per_page * constants.ARTICLES_ORPHANS_PERCENTAGE),
    )
    requested_page = get_page_number_from_request(request)
    articles_page = get_requested_page(articles_paginator, requested_page)
    reading_lists = ReadingList.objects.get_all_for_user(request.user)
    count_unread_articles_of_reading_lists = Article.objects.count_unread_articles_of_reading_lists(
        request.user, reading_lists
    )

    response_ctx = {
        **page_ctx,
        "base": {
            "fluid_content": True,
        },
        "reading_lists": reading_lists,
        "count_unread_articles_of_reading_lists": count_unread_articles_of_reading_lists,
        "count_articles_of_current_reading_list": articles_paginator.count,
        "articles_page": articles_page,
        "next_page_number": articles_page.next_page_number if articles_page.has_next() else None,
        "articles_paginator": articles_paginator,
        "elided_page_range": articles_paginator.get_elided_page_range(requested_page),
        "from_url": request.get_full_path(),
    }

    headers = {
        "Pragma": "no-cache",
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
    }

    if request.htmx:
        return TemplateResponse(
            request,
            "reading/list_of_articles.html#articles-page",
            response_ctx,
            status=status,
            headers=headers,
        )

    return TemplateResponse(
        request,
        "reading/list_of_articles.html",
        response_ctx,
        status=status,
        headers=headers,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csp_update(IMG_SRC="https:")
def tag_with_articles_view(request: AuthenticatedHttpRequest, tag_slug: str) -> TemplateResponse:
    displayed_tag = get_object_or_404(
        Tag,
        slug=tag_slug,
        user=request.user,
    )

    return list_or_update_articles(
        request,
        Article.objects.get_articles_of_tag(displayed_tag),
        _("Articles with tag '%(tag_title)s'") % {"tag_title": displayed_tag.title},
    )


@require_http_methods(["GET", "POST"])
@login_required
@csp_update(IMG_SRC="https:")
def external_tag_with_articles_view(
    request: AuthenticatedHttpRequest, tag: str
) -> TemplateResponse:
    tag_title = decode_external_tag(tag)
    return list_or_update_articles(
        request,
        Article.objects.get_articles_with_external_tag(request.user, tag_title),
        _("Articles with external tag '%(tag_title)s'") % {"tag_title": tag_title},
    )


def list_or_update_articles(
    request: AuthenticatedHttpRequest,
    articles_qs: ArticleQuerySet,
    page_title: str,
    extra_ctx: dict | None = None,
) -> TemplateResponse:
    extra_ctx = extra_ctx or {}
    tag_choices = Tag.objects.get_all_choices(request.user)
    status = HTTPStatus.OK
    form = UpdateArticlesForm(tag_choices=tag_choices)
    if request.method == "POST":
        status, form = update_list_of_articles(request, articles_qs, tag_choices)

    return _display_list_of_articles(
        request,
        articles_qs,
        {
            **extra_ctx,
            "page_title": page_title,
            "displayed_reading_list": None,
            "js_cfg": {},
            "update_articles_form": form,
        },
        status=status,
    )


class UpdateArticlesForm(forms.Form):
    add_tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to all articles of this search (not only the visible ones). "
            "To create a new tag, type and press enter."
        ),
    )
    remove_tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "Tags to dissociate with all articles of this search (not only the visible ones)."
        ),
        widget=MultipleTagsWidget(allow_new=False),
    )
    update_action = forms.ChoiceField(
        required=False,
        initial=constants.UpdateArticleActions.DO_NOTHING,
        choices=constants.UpdateArticleActions.choices,
    )

    def __init__(self, data=None, *, tag_choices: FormChoices, **kwargs):
        super().__init__(data, **kwargs)
        self._tag_value_choices = {choice[0] for choice in tag_choices}
        self.fields["add_tags"].choices = tag_choices  # type: ignore[attr-defined]
        self.fields["remove_tags"].choices = tag_choices  # type: ignore[attr-defined]

    def clean_remove_tags(self):
        for tag in self.cleaned_data["remove_tags"]:
            if tag not in self._tag_value_choices:
                raise ValidationError(
                    _("%s is not a known tag") % tag, code="tried-to-remove-inexistant-tag"
                )

        return self.cleaned_data["remove_tags"]

    def clean_update_action(self):
        if not self.cleaned_data.get("update_action"):
            return constants.UpdateArticleActions.DO_NOTHING

        return constants.UpdateArticleActions(self.cleaned_data["update_action"])


@transaction.atomic()
def update_list_of_articles(
    request: AuthenticatedHttpRequest, articles_qs: ArticleQuerySet, tag_choices: FormChoices
):
    form = UpdateArticlesForm(request.POST, tag_choices=tag_choices)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form

    if form.cleaned_data["add_tags"]:
        tags_to_add = Tag.objects.get_or_create_from_list(
            request.user, form.cleaned_data["add_tags"]
        )
        ArticleTag.objects.associate_articles_with_tags(
            articles_qs.all(),
            tags_to_add,
            tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
            readd_deleted=True,
        )

    if form.cleaned_data["remove_tags"]:
        # Note: the form validation assures us we won't create any tags here.
        tags_to_delete = Tag.objects.get_or_create_from_list(
            request.user, form.cleaned_data["remove_tags"]
        )
        ArticleTag.objects.dissociate_articles_with_tags(articles_qs.all(), tags_to_delete)

    articles_qs.all().update_articles_from_action(form.cleaned_data["update_action"])

    return HTTPStatus.OK, UpdateArticlesForm(tag_choices=tag_choices)
