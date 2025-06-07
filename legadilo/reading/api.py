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
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from http import HTTPStatus
from operator import xor
from typing import Annotated, Self

from django.shortcuts import get_object_or_404
from django.urls import reverse
from ninja import ModelSchema, Query, Router, Schema
from ninja.pagination import paginate
from pydantic import Field, model_validator

from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag, Tag
from legadilo.reading.services.article_fetching import (
    build_article_data_from_content,
    get_article_from_url,
)
from legadilo.reading.services.delete_article import delete_article
from legadilo.users.models import User
from legadilo.users.user_types import AuthenticatedApiRequest
from legadilo.utils.api import FIELD_UNSET, update_model_from_schema
from legadilo.utils.validators import (
    CleanedString,
    FullSanitizeValidator,
    ValidUrlValidator,
    remove_falsy_items,
)

reading_api_router = Router(tags=["reading"])


class OutTagSchema(ModelSchema):
    class Meta:
        model = Tag
        fields = ("title", "slug")


class OutArticleSchema(ModelSchema):
    tags: list[OutTagSchema] = Field(alias="tags_to_display")
    details_url: str

    @staticmethod
    def resolve_details_url(obj, context) -> str:
        url = reverse(
            "reading:article_details", kwargs={"article_id": obj.id, "article_slug": obj.slug}
        )
        return context["request"].build_absolute_uri(url)

    class Meta:
        model = Article
        exclude = ("user", "obj_created_at", "obj_updated_at")


class ArticleCreation(Schema):
    url: Annotated[str, ValidUrlValidator]
    title: Annotated[str, FullSanitizeValidator] = ""
    # We must not sanitize this yet: we need the raw content when building the article to fetch some
    # data (like authors, canonicals…). It will be sanitized later when we extract the actual
    # content of the article.
    content: str = ""
    tags: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()

    @model_validator(mode="after")
    def check_title_and_content(self) -> Self:
        if xor(len(self.title) > 0, len(self.content) > 0):
            raise ValueError("You must supply either both title and content or none of them")

        return self

    @property
    def has_data(self) -> bool:
        return bool(self.title) and bool(self.content)


@reading_api_router.post(
    "/articles/",
    response={HTTPStatus.CREATED: OutArticleSchema, HTTPStatus.OK: OutArticleSchema},
    url_name="create_article",
    summary="Create a new article",
)
def create_article_view(request: AuthenticatedApiRequest, payload: ArticleCreation):
    """Create an article either just with a link or with a link, a title and some content."""
    if payload.has_data:
        article_data = build_article_data_from_content(
            url=payload.url, title=payload.title, content=payload.content
        )
    else:
        article_data = get_article_from_url(payload.url)

    # Tags specified in article data are the raw tags used in feeds, they are not used to link an
    # article to tag objects.
    tags = Tag.objects.get_or_create_from_list(request.auth, payload.tags)
    article_data = article_data.model_copy(update={"tags": ()})

    save_results = Article.objects.save_from_list_of_data(
        request.auth, [article_data], tags, source_type=constants.ArticleSourceType.MANUAL
    )
    save_result = save_results[0]
    article = Article.objects.get_queryset().for_api().get(id=save_result.article.id)

    if save_result.was_created:
        return HTTPStatus.CREATED, article

    return HTTPStatus.OK, article


class ArticlesSearchQuery(Schema):
    urls: list[Annotated[str, ValidUrlValidator]] = Field(default_factory=list)


@reading_api_router.get(
    "/articles/",
    response={HTTPStatus.OK: list[OutArticleSchema]},
    url_name="list_articles",
    summary="List articles",
)
@paginate
def list_articles_view(request: AuthenticatedApiRequest, query: Query[ArticlesSearchQuery]):
    qs = Article.objects.get_queryset().for_user(request.auth).for_api()
    if query.urls:
        qs = qs.for_url_search(query.urls)

    return qs


@reading_api_router.get(
    "/articles/{int:article_id}/",
    url_name="get_article",
    response=OutArticleSchema,
    summary="View the details of a specific article",
)
def get_article_view(request: AuthenticatedApiRequest, article_id: int) -> Article:
    return get_object_or_404(
        Article.objects.get_queryset().for_api(), id=article_id, user=request.auth
    )


class ArticleUpdate(Schema):
    title: Annotated[str, FullSanitizeValidator] = FIELD_UNSET
    tags: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = FIELD_UNSET
    read_at: datetime | None = FIELD_UNSET
    is_favorite: bool = FIELD_UNSET
    is_for_later: bool = FIELD_UNSET
    reading_time: int = FIELD_UNSET


@reading_api_router.patch(
    "/articles/{int:article_id}/",
    response=OutArticleSchema,
    url_name="update_article",
    summary="Update an article",
)
def update_article_view(
    request: AuthenticatedApiRequest,
    article_id: int,
    payload: ArticleUpdate,
) -> Article:
    article = get_object_or_404(Article, id=article_id, user=request.auth)

    if payload.tags is not FIELD_UNSET:
        _update_article_tags(request.auth, article, payload.tags)

    update_model_from_schema(article, payload, excluded_fields={"tags"})

    return Article.objects.get_queryset().for_api().get(id=article_id)


def _update_article_tags(user: User, article: Article, new_tags: tuple[str, ...]):
    tags = Tag.objects.get_or_create_from_list(user, new_tags)
    ArticleTag.objects.associate_articles_with_tags(
        [article],
        tags,
        tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        readd_deleted=True,
    )
    ArticleTag.objects.dissociate_article_with_tags_not_in_list(article, tags)


@reading_api_router.delete(
    "/articles/{int:article_id}/",
    url_name="delete_article",
    response={HTTPStatus.NO_CONTENT: None},
    summary="Delete an article",
)
def delete_article_view(request: AuthenticatedApiRequest, article_id: int):
    article = get_object_or_404(Article, id=article_id, user=request.auth)

    delete_article(article)

    return HTTPStatus.NO_CONTENT, None


@reading_api_router.get("/tags/", url_name="list_tags", summary="List tags")
def list_tags_view(request: AuthenticatedApiRequest):
    choices, hierarchy = Tag.objects.get_all_choices_with_hierarchy(request.auth)

    tags = []

    for slug, title in choices:
        tags.append({
            "slug": slug,
            "title": title,
            "sub_tags": hierarchy.get(slug, []),
        })

    return {"count": len(tags), "items": tags}
