from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from legadilo.feeds import constants
from legadilo.feeds.models import Article
from legadilo.users.typing import AuthenticatedHttpRequest


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
