# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later


from http import HTTPStatus
from typing import Any
from urllib.parse import unquote_plus, urlencode

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csp import csp_override
from django.views.decorators.http import require_GET, require_http_methods

from config import settings
from legadilo.core.forms.fields import MultipleTagsField
from legadilo.core.forms.widgets import SelectMultipleAutocompleteWidget
from legadilo.core.utils.pagination import get_requested_page
from legadilo.core.utils.types import FormChoices
from legadilo.core.utils.validators import get_page_number_from_request
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag, ReadingList, Tag
from legadilo.reading.models.article import ArticleQuerySet
from legadilo.users.user_types import AuthenticatedHttpRequest

from ._utils import get_js_cfg_from_reading_list


@require_GET
@login_required
@csp_override({"img-src": settings.SECURE_CSP["img-src"] + ("https:",)})
def reading_list_with_articles_view(
    request: AuthenticatedHttpRequest, reading_list_slug: str | None = None
) -> HttpResponse:
    try:
        displayed_reading_list = ReadingList.objects.get_reading_list(
            request.user, reading_list_slug
        )
    except ReadingList.DoesNotExist as e:
        if reading_list_slug is not None:
            raise Http404("No reading list found") from e
        return HttpResponseRedirect(reverse("reading:default_reading_list"))

    return _display_list_of_articles(
        request,
        Article.objects.get_articles_of_reading_list(displayed_reading_list),
        {
            "page_title": displayed_reading_list.title,
            "displayed_reading_list": displayed_reading_list,
            "js_cfg": get_js_cfg_from_reading_list(displayed_reading_list),
            "search_query": urlencode(
                {
                    "read_status": displayed_reading_list.read_status,
                    "favorite_status": displayed_reading_list.favorite_status,
                    "for_later_status": displayed_reading_list.for_later_status,
                    "articles_max_age_value": displayed_reading_list.articles_max_age_value,
                    "articles_max_age_unit": displayed_reading_list.articles_max_age_unit,
                    "articles_reading_time": displayed_reading_list.articles_reading_time,
                    "articles_reading_time_operator": displayed_reading_list.articles_reading_time_operator,  # noqa: E501
                    "include_tag_operator": displayed_reading_list.include_tag_operator,
                    "tags_to_include": displayed_reading_list.reading_list_tags.get_selected_values(
                        constants.ReadingListTagFilterType.INCLUDE
                    ),
                    "exclude_tag_operator": displayed_reading_list.exclude_tag_operator,
                    "tags_to_exclude": displayed_reading_list.reading_list_tags.get_selected_values(
                        constants.ReadingListTagFilterType.EXCLUDE
                    ),
                },
                doseq=True,
            ),
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
        else constants.MAX_OBJECTS_PER_PAGE
    )
    articles_paginator = Paginator(
        articles_qs,
        articles_per_page,
        # Prevent pages with less that 10% of the number of articles. Display them on the previous
        # page instead of as orphans.
        orphans=int(articles_per_page * constants.PAGINATION_ORPHANS_PERCENTAGE),
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

    return TemplateResponse(
        request,
        "reading/list_of_articles.html",
        response_ctx,
        status=status,
        headers=headers,
    )


@require_http_methods(["GET", "POST"])
@login_required
@csp_override({"img-src": settings.SECURE_CSP["img-src"] + ("https:",)})
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
        {"tags_to_include": [displayed_tag.slug]},
    )


@require_http_methods(["GET", "POST"])
@login_required
@csp_override({"img-src": settings.SECURE_CSP["img-src"] + ("https:",)})
def external_tag_with_articles_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    external_tag = request.GET.get("tag", "")
    external_tag = unquote_plus(external_tag)

    articles_qs = (
        Article.objects.get_articles_with_external_tag(request.user, external_tag)
        if external_tag
        else Article.objects.get_queryset().none()
    )
    search_dict = {"external_tags_to_include": [external_tag]} if external_tag else {}

    return list_or_update_articles(
        request,
        articles_qs,
        _("Articles with external tag '%(tag_title)s'") % {"tag_title": external_tag},
        search_dict,
    )


def list_or_update_articles(
    request: AuthenticatedHttpRequest,
    articles_qs: ArticleQuerySet,
    page_title: str,
    search_dict: dict,
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
            "search_query": urlencode(search_dict, doseq=True),
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
        widget=SelectMultipleAutocompleteWidget(allow_new=False, empty_label=_("Choose tags")),
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
                    _("'%s' is not a known tag.") % tag, code="tried-to-remove-inexistent-tag"
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
        ArticleTag.objects.associate_articles_with_tags(articles_qs.all(), tags_to_add)

    if form.cleaned_data["remove_tags"]:
        # Note: the form validation assures us we won't create any tags here.
        tags_to_delete = Tag.objects.get_or_create_from_list(
            request.user, form.cleaned_data["remove_tags"]
        )
        ArticleTag.objects.dissociate_articles_with_tags(articles_qs.all(), tags_to_delete)

    articles_qs.all().update_articles_from_action(form.cleaned_data["update_action"])

    return HTTPStatus.OK, UpdateArticlesForm(tag_choices=tag_choices)
