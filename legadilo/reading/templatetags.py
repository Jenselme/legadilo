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

from urllib.parse import unquote

from django.template.defaultfilters import stringfilter, urlencode
from django.template.defaulttags import register
from django.urls import reverse
from django.utils.safestring import mark_safe
from markdown import Markdown

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
def encode_external_tag(tag: str) -> str:
    return urlencode(tag.replace("/", "------"))


@register.filter
def decode_external_tag(tag: str) -> str:
    return unquote(tag).replace("------", "/")


@register.filter
@stringfilter
def markdown(value: str) -> str:
    md = Markdown(extensions=["fenced_code"])
    return mark_safe(md.convert(value))  # noqa: S308 valid use of markup safe.
