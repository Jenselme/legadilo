from django.template.defaulttags import register
from django.urls import reverse

from legadilo.feeds import constants
from legadilo.feeds.models import Article, ReadingList


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


@register.filter
def for_later_action_url(article: Article) -> str:
    action = (
        constants.UpdateArticleActions.UNMARK_AS_FOR_LATER
        if article.is_for_later
        else constants.UpdateArticleActions.MARK_AS_FOR_LATER
    )

    return reverse(
        "feeds:update_article", kwargs={"article_id": article.id, "update_action": action}
    )


@register.filter
def opened_action_url(article: Article) -> str:
    return reverse(
        "feeds:update_article",
        kwargs={
            "article_id": article.id,
            "update_action": constants.UpdateArticleActions.MARK_AS_OPENED,
        },
    )


@register.filter
def delete_action_url(article: Article) -> str:
    return reverse("feeds:delete_article", kwargs={"article_id": article.id})


@register.filter
def update_tags_action_url(article: Article) -> str:
    return reverse("feeds:update_article_tags", kwargs={"article_id": article.id})


@register.filter
def article_details_url(article: Article) -> str:
    return reverse(
        "feeds:article_details", kwargs={"article_id": article.id, "article_slug": article.slug}
    )


@register.filter
def reading_list_url(reading_list: ReadingList) -> str:
    if reading_list.is_default:
        return reverse("feeds:default_reading_list")

    return reverse("feeds:reading_list", kwargs={"reading_list_slug": reading_list.slug})
