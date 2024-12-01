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
from datetime import datetime
from http import HTTPStatus
from operator import xor
from typing import Annotated, Self

from asgiref.sync import sync_to_async
from django.shortcuts import aget_object_or_404
from ninja import ModelSchema, Router, Schema
from ninja.pagination import paginate
from pydantic import Field, model_validator

from config import settings
from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag, Tag
from legadilo.reading.services.article_fetching import (
    build_article_data_from_content,
    get_article_from_url,
)
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

    class Meta:
        model = Article
        exclude = ("user", "obj_created_at", "obj_updated_at")


class ArticleCreation(Schema):
    link: Annotated[str, ValidUrlValidator]
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
    response={HTTPStatus.CREATED: OutArticleSchema},
    url_name="create_article",
    summary="Create a new article",
)
async def create_article_view(request: AuthenticatedApiRequest, payload: ArticleCreation):
    """Create an article either just with a link or with a link, a title and some content."""
    if payload.has_data:
        article_data = build_article_data_from_content(
            url=payload.link, title=payload.title, content=payload.content
        )
    else:
        article_data = await get_article_from_url(payload.link)

    # Tags specified in article data are the raw tags used in feeds, they are not used to link an
    # article to tag objects.
    tags = await sync_to_async(Tag.objects.get_or_create_from_list)(request.auth, payload.tags)
    article_data = article_data.model_copy(update={"tags": ()})

    articles = await sync_to_async(Article.objects.update_or_create_from_articles_list)(
        request.auth, [article_data], tags, source_type=constants.ArticleSourceType.MANUAL
    )
    return HTTPStatus.CREATED, await Article.objects.get_queryset().for_api().aget(
        id=articles[0].id
    )


@reading_api_router.get(
    "/articles/{int:article_id}/",
    url_name="get_article",
    response=OutArticleSchema,
    summary="View the details of a specific article",
)
async def get_article_view(request: AuthenticatedApiRequest, article_id: int) -> Article:
    return await aget_object_or_404(
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
async def update_article_view(
    request: AuthenticatedApiRequest,
    article_id: int,
    payload: ArticleUpdate,
) -> Article:
    article = await aget_object_or_404(Article, id=article_id, user=request.auth)

    if payload.tags is not FIELD_UNSET:
        await _update_article_tags(request.auth, article, payload.tags)

    await update_model_from_schema(article, payload, excluded_fields={"tags"})

    return await Article.objects.get_queryset().for_api().aget(id=article_id)


async def _update_article_tags(user: User, article: Article, new_tags: tuple[str, ...]):
    tags = await sync_to_async(Tag.objects.get_or_create_from_list)(user, new_tags)
    await sync_to_async(ArticleTag.objects.associate_articles_with_tags)(
        [article],
        tags,
        tagging_reason=constants.TaggingReason.ADDED_MANUALLY,
        readd_deleted=True,
    )
    await sync_to_async(ArticleTag.objects.dissociate_article_with_tags_not_in_list)(article, tags)


@reading_api_router.delete(
    "/articles/{int:article_id}/",
    url_name="delete_article",
    response={HTTPStatus.NO_CONTENT: None},
    summary="Delete an article",
)
async def delete_article_view(request: AuthenticatedApiRequest, article_id: int):
    article = await aget_object_or_404(Article, id=article_id, user=request.auth)

    await article.adelete()

    return HTTPStatus.NO_CONTENT, None


@reading_api_router.get(
    "/tags/", response=list[OutTagSchema], url_name="list_tags", summary="List tags"
)
# Let's get all tags.
@paginate(page_size=settings.NINJA_PAGINATION_MAX_LIMIT * 4)
async def list_tags_view(request: AuthenticatedApiRequest):  # noqa: RUF029 paginate is async!
    return Tag.objects.get_queryset().for_user(request.auth)
