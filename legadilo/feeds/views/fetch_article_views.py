from http import HTTPStatus

import httpx
from asgiref.sync import sync_to_async
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from legadilo.core.forms.fields import MultipleTagsField
from legadilo.feeds import constants
from legadilo.feeds.models import Article, Tag
from legadilo.feeds.utils.article_fetching import (
    ArticleTooBigError,
    get_article_from_url,
)
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.decorators import alogin_required
from legadilo.utils.urls import validate_referer_url


class FetchArticleForm(forms.Form):
    url = forms.URLField(
        assume_scheme="https",  # type: ignore[call-arg]
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
            success_message=_("Article '%s' successfully added!"),
            no_content_message=_(
                "The article '%s' was added but we failed to fetch its content. "
                "Please check that it really points to an article."
            ),
        )

    return TemplateResponse(
        request, "feeds/add_article.html", {"form": form, "tags": Tag.objects.all()}, status=status
    )


@require_http_methods(["POST"])
@alogin_required
async def refetch_article_view(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    await _handle_save(
        request,
        [],
        success_message=_("Article '%s' successfully re-fetched!"),
        no_content_message=_(
            "The article '%s' was re-fetched but we failed to fetch its content. "
            "Please check that it really points to an article."
        ),
    )

    return HttpResponseRedirect(
        validate_referer_url(request, reverse("feeds:default_reading_list"))
    )


async def _handle_save(
    request: AuthenticatedHttpRequest,
    tag_choices: list[tuple[str, str]],
    *,
    success_message,
    no_content_message,
):
    form = FetchArticleForm(request.POST, tag_choices=tag_choices)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form

    try:
        article_data = await get_article_from_url(form.cleaned_data["url"])
        tags = await sync_to_async(Tag.objects.get_or_create_from_list)(
            request.user, form.cleaned_data["tags"]
        )
        article = (
            await sync_to_async(Article.objects.update_or_create_from_articles_list)(
                request.user,
                [article_data],
                tags,
                source_type=constants.ArticleSourceType.MANUAL,
            )
        )[0]
    except httpx.HTTPError:
        messages.error(
            request,
            _(
                "Failed to fetch the article. Please check that the URL you entered is correct, "
                "that the article exists and is accessible."
            ),
        )
        return HTTPStatus.NOT_ACCEPTABLE, form
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
        messages.success(request, success_message % article.title)
    return HTTPStatus.CREATED, form
