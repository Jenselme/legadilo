from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET, require_POST

from legadilo.feeds import constants
from legadilo.feeds.models import Article
from legadilo.users.typing import AuthenticatedHttpRequest


@require_GET
@login_required
def article_details_view(
    request: AuthenticatedHttpRequest, article_id: int, article_slug: str
) -> TemplateResponse:
    article = get_object_or_404(
        Article.objects.get_queryset().for_details(),
        id=article_id,
        slug=article_slug,
        feed__user=request.user,
    )

    return TemplateResponse(
        request,
        "feeds/article_details.html",
        {
            "article": article,
        },
    )


@require_POST
@login_required
def update_article_view(
    request: AuthenticatedHttpRequest,
    article_id: int,
    update_action: constants.UpdateArticleActions,
) -> HttpResponse:
    article = get_object_or_404(Article, id=article_id, feed__user=request.user)
    article.update_article(update_action)
    article.save()

    return _redirect_to_origin(request)


def _redirect_to_origin(request: AuthenticatedHttpRequest) -> HttpResponseRedirect:
    referer = request.headers.get("Referer")
    parsed_referer = urlparse(referer)
    redirect_url = request.build_absolute_uri(str(parsed_referer.path))
    if parsed_referer.query:
        redirect_url += "?" + str(parsed_referer.query)
    if parsed_referer.fragment:
        redirect_url += "#" + str(parsed_referer.fragment)
    return HttpResponseRedirect(redirect_url)
