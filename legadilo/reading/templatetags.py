# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.template.defaultfilters import stringfilter
from django.template.defaulttags import register
from django.urls import reverse
from markdown import Markdown

from legadilo.core.utils.security import sanitize_keep_safe_tags
from legadilo.reading import constants
from legadilo.reading.models import Article, ReadingList


@register.filter
def read_action_url(article: Article) -> str:
    action = (
        constants.UpdateArticleActions.MARK_AS_UNREAD
        if article.is_read
        else constants.UpdateArticleActions.MARK_AS_READ
    )
    return reverse(
        "reading:update_article", kwargs={"article_id": article.id, "update_action": action}
    )


@register.filter
def favorite_action_url(article: Article) -> str:
    action = (
        constants.UpdateArticleActions.UNMARK_AS_FAVORITE
        if article.is_favorite
        else constants.UpdateArticleActions.MARK_AS_FAVORITE
    )
    return reverse(
        "reading:update_article", kwargs={"article_id": article.id, "update_action": action}
    )


@register.filter
def for_later_action_url(article: Article) -> str:
    action = (
        constants.UpdateArticleActions.UNMARK_AS_FOR_LATER
        if article.is_for_later
        else constants.UpdateArticleActions.MARK_AS_FOR_LATER
    )

    return reverse(
        "reading:update_article", kwargs={"article_id": article.id, "update_action": action}
    )


@register.filter
def opened_action_url(article: Article) -> str:
    return reverse(
        "reading:update_article",
        kwargs={
            "article_id": article.id,
            "update_action": constants.UpdateArticleActions.MARK_AS_OPENED,
        },
    )


@register.filter
def article_details_url(article: Article) -> str:
    return reverse(
        "reading:article_details", kwargs={"article_id": article.id, "article_slug": article.slug}
    )


@register.filter
def reading_list_url(reading_list: ReadingList) -> str:
    if reading_list.is_default:
        return reverse("reading:default_reading_list")

    return reverse("reading:reading_list", kwargs={"reading_list_slug": reading_list.slug})


@register.filter
def article_action_indicator(article: Article) -> str:
    return f"icon-indicator-{article.id}"


@register.filter
def article_card_id(article: Article) -> str:
    return f"article-card-{article.id}"


@register.filter
def delete_article_form_id(article: Article) -> str:
    return f"delete-article-{article.id}"


@register.filter
def update_article_form_id(article: Article) -> str:
    return f"update-article-actions-form-{article.id}"


@register.filter
@stringfilter
def markdown(value: str) -> str:
    md = Markdown(extensions=["fenced_code"])
    rendered_value = md.convert(value)
    cleaned_value = sanitize_keep_safe_tags(rendered_value)
    return cleaned_value.strip()


@register.filter
def open_original_with_link(article: Article) -> bool:
    return not article.content or bool(
        article.main_feed and article.main_feed.open_original_url_by_default
    )
