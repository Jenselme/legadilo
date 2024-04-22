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

from legadilo.feeds import constants
from legadilo.feeds.models import Article
from legadilo.feeds.utils.article_fetching import (
    ArticleTooBigError,
    get_article_from_url,
)
from legadilo.users.typing import AuthenticatedHttpRequest
from legadilo.utils.decorators import alogin_required
from legadilo.utils.urls import validate_referer_url


class AddArticleForm(forms.Form):
    url = forms.URLField(
        assume_scheme="https",  # type: ignore[call-arg]
        help_text=_("URL of the article to add."),
    )

    class Meta:
        fields = ("url",)


@require_http_methods(["GET", "POST"])
@alogin_required
async def add_article_view(request: AuthenticatedHttpRequest) -> TemplateResponse:
    form = AddArticleForm()
    status = HTTPStatus.OK

    if request.method == "POST":
        status, form = await _handle_save(request)

    return TemplateResponse(request, "feeds/add_article.html", {"form": form}, status=status)


@require_http_methods(["POST"])
@alogin_required
async def refetch_article_view(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    await _handle_save(request)

    return HttpResponseRedirect(
        validate_referer_url(request, reverse("feeds:default_reading_list"))
    )


async def _handle_save(request: AuthenticatedHttpRequest):
    form = AddArticleForm(request.POST)
    if not form.is_valid():
        return HTTPStatus.BAD_REQUEST, form

    try:
        article_data = await get_article_from_url(form.cleaned_data["url"])
        article = (
            await sync_to_async(Article.objects.update_or_create_from_articles_list)(
                request.user,
                [article_data],
                [],
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
            request, _("The article you are trying to add is too big and cannot be processed.")
        )
        return HTTPStatus.BAD_REQUEST, form

    # Empty form after success
    form = AddArticleForm()
    if not article.content:
        messages.warning(
            request,
            _(
                "The article '%s' was added but we failed to fetch its content. "
                "Please check that it really points to an article."
            )
            % article.title,
        )
    else:
        messages.success(request, _("Article '%s' successfully added!") % article.title)
    return HTTPStatus.CREATED, form
