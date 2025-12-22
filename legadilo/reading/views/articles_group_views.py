#  SPDX-FileCopyrightText: 2025 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus
from typing import cast

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, QueryDict
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.csp import csp_override
from django.views.decorators.http import require_GET, require_http_methods

from legadilo.core.forms.widgets import SelectMultipleAutocompleteWidget
from legadilo.core.utils.pagination import get_requested_page
from legadilo.core.utils.types import FormChoices
from legadilo.core.utils.validators import get_page_number_from_request
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticlesGroup, Tag
from legadilo.reading.models.articles_group import ArticlesGroupQuerySet
from legadilo.reading.templatetags import articles_group_details_url
from legadilo.users.models import User
from legadilo.users.user_types import AuthenticatedHttpRequest


@require_http_methods(["GET", "POST"])
@login_required
def articles_group_details_view(
    request: AuthenticatedHttpRequest, group_id: int, group_slug: str
) -> TemplateResponse | HttpResponseRedirect:
    group = _get_group(request.user, group_id, group_slug)

    if request.method == "POST" and "mark_all_as_read" in request.POST:
        articles_qs = Article.objects.filter(group=group)
        articles_qs.update_articles_from_action(constants.UpdateArticleActions.MARK_AS_READ)  # type: ignore[attr-defined]
        group = _get_group(request.user, group_id, group_slug)
    elif request.method == "POST" and request.POST.get("action") == "delete_group":
        group.delete()
        return HttpResponseRedirect(reverse("reading:articles_groups_list"))
    elif request.method == "POST" and request.POST.get("action") == "delete_group_and_all_articles":
        group.articles.all().delete()
        group.delete()
        return HttpResponseRedirect(reverse("reading:articles_groups_list"))

    return TemplateResponse(
        request,
        "reading/articles_group_details.html",
        {
            "group": group,
            "from_url": articles_group_details_url(group),
        },
    )


def _get_group(user: User, group_id: int, group_slug: str) -> ArticlesGroup:
    return get_object_or_404(
        ArticlesGroup.objects.get_queryset().for_details(user), id=group_id, slug=group_slug
    )


@require_http_methods(["GET", "POST"])
@login_required
@csp_override({"img-src": settings.SECURE_CSP["img-src"] + ("https:",)})
def article_groups_read_all_articles_view(
    request: AuthenticatedHttpRequest, group_id: int, group_slug: str
) -> TemplateResponse | HttpResponseRedirect:
    group = _get_group(request.user, group_id, group_slug)

    if request.method == "POST":
        articles_qs = Article.objects.filter(group=group)
        articles_qs.update_articles_from_action(constants.UpdateArticleActions.MARK_AS_READ)  # type: ignore[attr-defined]
        return HttpResponseRedirect(articles_group_details_url(group))

    return TemplateResponse(
        request,
        "reading/articles_group_read_all_articles.html",
        {
            "base": {
                "fluid_content": True,
            },
            "group": group,
        },
    )


class SearchArticlesGroupsForm(forms.Form):
    q = forms.CharField(required=False, min_length=3, label="Search text")
    tags = forms.MultipleChoiceField(
        required=False,
        choices=[],
        help_text="Find groups containing all these tags",
        widget=SelectMultipleAutocompleteWidget(allow_new=False, empty_label="Choose tags"),
    )

    def __init__(self, data: QueryDict, *, tag_choices: FormChoices):
        super().__init__(data.copy())
        self.fields["tags"].choices = tag_choices  # type: ignore[attr-defined]

    def clean_q(self):
        q = self.cleaned_data["q"]
        return q.strip()

    @property
    def is_filled(self) -> bool:
        return bool(self.cleaned_data.get("q") or self.cleaned_data.get("tags"))


@require_GET
@login_required
def articles_groups_list_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    form = SearchArticlesGroupsForm(
        request.GET, tag_choices=Tag.objects.get_all_choices(request.user)
    )
    if form.is_valid():
        groups_qs = ArticlesGroup.objects.list_for_admin(
            request.user, form.cleaned_data["q"], form.cleaned_data["tags"]
        )
        status = HTTPStatus.OK
    else:
        groups_qs = cast(ArticlesGroupQuerySet, ArticlesGroup.objects.none())
        status = HTTPStatus.BAD_REQUEST
    groups_paginator = Paginator(
        groups_qs,
        constants.MAX_OBJECTS_PER_PAGE,
        orphans=int(constants.MAX_OBJECTS_PER_PAGE * constants.PAGINATION_ORPHANS_PERCENTAGE),
    )
    requested_page = get_page_number_from_request(request)
    groups_page = get_requested_page(groups_paginator, requested_page)

    return TemplateResponse(
        request,
        "reading/articles_groups_list.html",
        {
            "groups_page": groups_page,
            "groups_paginator": groups_paginator,
            "elided_page_range": groups_paginator.get_elided_page_range(requested_page),
            "form": form,
        },
        status=status,
    )
