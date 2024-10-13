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

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from legadilo.feeds.models import FeedDeletedArticle
from legadilo.reading import constants as reading_constants
from legadilo.reading.models import Article
from legadilo.reading.services.views import get_from_url_for_article_details
from legadilo.reading.templatetags import article_card_id
from legadilo.reading.views.article_actions_views import (
    redirect_to_reading_list,
    update_article_card,
)
from legadilo.users.user_types import AuthenticatedHttpRequest


@require_POST
@login_required
def delete_article_view(request: AuthenticatedHttpRequest, article_id: int) -> HttpResponse:
    """Delete article either a manual one or if it's linked with a feed.

    If it's linked with a feed, we also update the FeedDeletedArticle to prevent re-adding this
    article again.
    """
    article = get_object_or_404(
        Article.objects.get_queryset().for_deletion(), id=article_id, user=request.user
    )
    hx_target = f"#{article_card_id(article)}"

    FeedDeletedArticle.objects.delete_article(article)

    for_article_details = request.POST.get("for_article_details", "")
    if for_article_details:
        return redirect_to_reading_list(request)

    if not request.htmx:
        from_url = get_from_url_for_article_details(request, request.POST)
        return HttpResponseRedirect(from_url)

    return update_article_card(
        request,
        article,
        reading_constants.UpdateArticleActions.DO_NOTHING,
        hx_target=hx_target,
        delete_article_card=True,
    )