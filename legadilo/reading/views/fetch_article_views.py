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

from http import HTTPStatus

import httpx
from asgiref.sync import sync_to_async
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.core.forms.fields import MultipleTagsField
from legadilo.reading import constants
from legadilo.reading.models import Article, Tag
from legadilo.reading.services.article_fetching import (
    ArticleTooBigError,
    get_article_from_url,
)
from legadilo.reading.templatetags import article_details_url
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.decorators import alogin_required
from legadilo.utils.exceptions import extract_debug_information, format_exception
from legadilo.utils.urls import add_query_params, pop_query_param, validate_referer_url


class FetchArticleForm(forms.Form):
    url = forms.URLField(
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
@alogin_required
async def add_article_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    tag_choices = await sync_to_async(Tag.objects.get_all_choices)(request.user)
    form = FetchArticleForm(tag_choices=tag_choices)
    status = HTTPStatus.OK

    if request.method == "POST":
        status, form = await _handle_save(
            request,
            tag_choices,
            success_message=_("Article '<a href=\"{}\">{}</a>' successfully added!"),
            no_content_message=_(
                "The article '%s' was added but we failed to fetch its content. "
                "Please check that it really points to an article."
            ),
            force_update=False,
        )

    return TemplateResponse(
        request,
        "reading/add_article.html",
        {"form": form, "tags": Tag.objects.all()},
        status=status,
    )


@require_http_methods(["POST"])
@alogin_required
async def refetch_article_view(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    article = await sync_to_async(get_object_or_404)(
        Article, link=request.POST.get("url"), user=request.user
    )
    await _handle_save(
        request,
        [],
        success_message=_("Article '<a href=\"{}\">{}</a>' successfully re-fetched!"),
        no_content_message=_(
            "The article '%s' was re-fetched but we failed to fetch its content. "
            "Please check that it really points to an article."
        ),
        force_update=True,
    )

    await article.arefresh_from_db()
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


async def _handle_save(
    request: AuthenticatedHttpRequest,
    tag_choices: list[tuple[str, str]],
    *,
    success_message,
    no_content_message,
    force_update: bool,
):
    form = FetchArticleForm(request.POST, tag_choices=tag_choices)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form

    tags = await sync_to_async(Tag.objects.get_or_create_from_list)(
        request.user, form.cleaned_data["tags"]
    )
    article_link = form.cleaned_data["url"]
    try:
        article_data = await get_article_from_url(article_link)
        article = (
            await sync_to_async(Article.objects.update_or_create_from_articles_list)(
                request.user,
                [article_data],
                tags,
                source_type=constants.ArticleSourceType.MANUAL,
                force_update=force_update,
            )
        )[0]
    except httpx.HTTPError as e:
        article, created = await sync_to_async(Article.objects.create_invalid_article)(
            request.user,
            article_link,
            tags,
            error_message=format_exception(e),
            technical_debug_data=extract_debug_information(e),
        )
        if created:
            messages.warning(
                request,
                _(
                    "Failed to fetch the article. Please check that the URL you entered is "
                    "correct, that the article exists and is accessible. We added its URL directly."
                ),
            )
            return HTTPStatus.CREATED, form
        messages.error(
            request,
            _(
                "Failed to fetch the article. Please check that the URL you entered is "
                "correct, that the article exists and is accessible. It was added before, "
                "please check its link."
            ),
        )
        return HTTPStatus.BAD_REQUEST, form
    except ArticleTooBigError:
        messages.error(
            request, _("The article you are trying to fetch is too big and cannot be processed.")
        )
        return HTTPStatus.BAD_REQUEST, form

    # Empty form after success
    form = FetchArticleForm(tag_choices=tag_choices)
    if not article.content:
        messages.warning(
            request,
            no_content_message % article.title,
        )
    else:
        messages.success(
            request,
            format_html(success_message, str(article_details_url(article)), article.title),
        )
    return HTTPStatus.CREATED, form
