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

import httpx
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from pydantic import ValidationError as PydanticValidationError

from legadilo.core.forms.fields import MultipleTagsField
from legadilo.reading import constants
from legadilo.reading.models import Article, Tag
from legadilo.reading.models.article import SaveArticleResult
from legadilo.reading.services.article_fetching import (
    ArticleTooBigError,
    get_article_from_url,
)
from legadilo.reading.templatetags import article_details_url
from legadilo.users.user_types import AuthenticatedHttpRequest
from legadilo.utils.exceptions import extract_debug_information, format_exception
from legadilo.utils.urls import add_query_params, pop_query_param, validate_referer_url


class FetchArticleForm(forms.Form):
    url = forms.URLField(
        max_length=2048,
        assume_scheme="https",
        help_text=_("URL of the article to add."),
    )
    tags = MultipleTagsField(
        required=False,
        choices=[],
        help_text=_(
            "Tags to associate to this article. To create a new tag, type and press enter."
        ),
    )

    class Meta:
        fields = ("url", "tags")

    def __init__(self, *args, tag_choices: list[tuple[str, str]], **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tags"].choices = tag_choices  # type: ignore[attr-defined]


@require_http_methods(["GET", "POST"])
@login_required
def add_article_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    tag_choices, hierarchy = Tag.objects.get_all_choices_with_hierarchy(request.user)
    form = FetchArticleForm(tag_choices=tag_choices)
    status = HTTPStatus.OK

    if request.method == "POST":
        status, form, save_result = _handle_save(request, tag_choices, force_update=False)
        _handle_add_article_save_result(request, save_result)

    return TemplateResponse(
        request,
        "reading/add_article.html",
        {
            "form": form,
            "tags_hierarchy": hierarchy,
        },
        status=status,
    )


def _handle_add_article_save_result(
    request: AuthenticatedHttpRequest, save_result: SaveArticleResult | None
):
    if not save_result:
        return

    details_url = str(article_details_url(save_result.article))
    sanitized_title = mark_safe(save_result.article.title)  # noqa: S308 valid use of markup safe.

    if not save_result.article.content:
        messages.warning(
            request,
            format_html(
                str(
                    _(
                        "The article '<a href=\"{}\">{}</a>' was added but we failed to fetch its content. "  # noqa: E501
                        "Please check that it really points to an article."
                    )
                ),
                details_url,
                sanitized_title,
            ),
        )
    elif save_result.was_created:
        messages.success(
            request,
            format_html(
                str(_("Article '<a href=\"{}\">{}</a>' successfully added!")),
                details_url,
                sanitized_title,
            ),
        )
    else:
        messages.info(
            request,
            format_html(
                str(_("Article '<a href=\"{}\">{}</a>' already existed.")),
                details_url,
                sanitized_title,
            ),
        )


@require_http_methods(["POST"])
@login_required
def refetch_article_view(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    article = get_object_or_404(Article, url=request.POST.get("url"), user=request.user)
    _status, _form, save_result = _handle_save(
        request,
        [],
        force_update=True,
    )

    _handle_refetch_article_save_result(request, save_result)

    article.refresh_from_db()
    _url, from_url = pop_query_param(
        validate_referer_url(request, reverse("reading:default_reading_list")), "from_url"
    )
    new_article_url = add_query_params(
        reverse(
            "reading:article_details",
            kwargs={"article_id": article.id, "article_slug": article.slug},
        ),
        {"from_url": from_url},
    )

    return HttpResponseRedirect(new_article_url)


def _handle_refetch_article_save_result(
    request: AuthenticatedHttpRequest, save_result: SaveArticleResult | None
):
    if not save_result:
        return

    if not save_result.article.content:
        messages.warning(
            request,
            _(
                "The article was re-fetched but we failed to fetch its content. "
                "Please check that it really points to an article."
            ),
        )
    else:
        messages.success(request, _("The article was successfully re-fetched!"))


def _handle_save(
    request: AuthenticatedHttpRequest,
    tag_choices: list[tuple[str, str]],
    *,
    force_update: bool,
) -> tuple[HTTPStatus, FetchArticleForm, SaveArticleResult | None]:
    form = FetchArticleForm(request.POST, tag_choices=tag_choices)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form, None

    tags = Tag.objects.get_or_create_from_list(request.user, form.cleaned_data["tags"])
    article_url = form.cleaned_data["url"]
    try:
        article_data = get_article_from_url(article_url)
        save_result = (
            Article.objects.save_from_list_of_data(
                request.user,
                [article_data],
                tags,
                source_type=constants.ArticleSourceType.MANUAL,
                force_update=force_update,
            )
        )[0]
    except (httpx.HTTPError, ArticleTooBigError, PydanticValidationError) as e:
        invalid_article, created = Article.objects.create_invalid_article(
            request.user,
            article_url,
            tags,
            error_message=format_exception(e),
            technical_debug_data=extract_debug_information(e),
        )
        if created and isinstance(e, httpx.HTTPError):
            messages.warning(
                request,
                format_html(
                    str(
                        _(
                            "Failed to fetch the article. Please check that the URL you entered is "
                            "correct, that the article exists and is accessible. "
                            "We added its URL directly. "
                            'Go <a href="{}">there</a> to access it.'
                        )
                    ),
                    str(article_details_url(invalid_article)),
                ),
            )
            return HTTPStatus.CREATED, form, None
        if created:
            messages.warning(
                request,
                format_html(
                    str(
                        _(
                            "The article you are trying to fetch is too big and cannot be processed. "  # noqa: E501
                            "We added its URL directly. "
                            'Go <a href="{}">there</a> to access it.'
                        )
                    ),
                    str(article_details_url(invalid_article)),
                ),
            )
            return HTTPStatus.CREATED, form, None
        messages.error(
            request,
            _(
                "Failed to fetch the article. Please check that the URL you entered is "
                "correct, that the article exists and is accessible. It was added before, "
                "please check its link."
            ),
        )
        return HTTPStatus.BAD_REQUEST, form, None

    # Empty form after success
    form = FetchArticleForm(tag_choices=tag_choices)
    status = HTTPStatus.CREATED

    return status, form, save_result
