from django.template.defaulttags import register
from django.urls import reverse

from legadilo.feeds import constants
from legadilo.feeds.models import Article


@register.filter
def read_action_url(article: Article) -> str:
    action = (
        constants.UpdateArticleActions.MARK_AS_UNREAD
        if article.is_read
        else constants.UpdateArticleActions.MARK_AS_READ
    )
    return reverse(
        "feeds:update_article", kwargs={"article_id": article.id, "update_action": action}
    )


@register.filter
def favorite_action_url(article: Article) -> str:
    action = (
        constants.UpdateArticleActions.UNMARK_AS_FAVORITE
        if article.is_favorite
        else constants.UpdateArticleActions.MARK_AS_FAVORITE
    )
    return reverse(
        "feeds:update_article", kwargs={"article_id": article.id, "update_action": action}
    )