# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from http import HTTPStatus
from typing import Annotated, Self

import httpx
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from ninja import ModelSchema, Query, Router, Schema
from ninja.pagination import paginate
from pydantic import Field, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic.json_schema import SkipJsonSchema

from legadilo.reading import constants
from legadilo.reading.models import Article, ArticleTag, Comment, ReadingList, Tag
from legadilo.reading.models.article import ArticleFullTextSearchQuery
from legadilo.reading.services.article_fetching import (
    ArticleData,
    ArticleTooBigError,
    build_article_data_from_content,
    get_article_from_url,
)
from legadilo.users.models import User
from legadilo.users.user_types import AuthenticatedApiRequest
from legadilo.utils.api import ApiError, NotSet, update_model_from_schema
from legadilo.utils.validators import (
    CleanedString,
    ContentType,
    ValidUrlValidator,
    remove_falsy_items,
)

reading_api_router = Router(tags=["reading"])


class OutTagSchema(ModelSchema):
    class Meta:
        model = Tag
        fields = ("title", "slug")


class OutCommentSchema(ModelSchema):
    class Meta:
        model = Comment
        fields = ("text", "created_at", "updated_at")


class OutArticleSchema(ModelSchema):
    tags: list[OutTagSchema] = Field(alias="tags_to_display")
    comments: list[OutCommentSchema]
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
    title: CleanedString = ""
    # We must not sanitize this yet: we need the raw content when building the article to fetch some
    # data (like authors, canonicals…). It will be sanitized later when we extract the actual
    # content of the article.
    content: str = ""
    content_type: ContentType = "text/html"
    tags: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()

    @model_validator(mode="after")
    def check_title_and_content(self) -> Self:
        if len(self.title) == 0 and len(self.content) > 0:
            raise ValueError("Title is mandatory when content is provided.")

        return self

    @property
    def has_data(self) -> bool:
        return bool(self.title)


@reading_api_router.post(
    "/articles/",
    response={
        HTTPStatus.CREATED: OutArticleSchema,
        HTTPStatus.OK: OutArticleSchema,
        HTTPStatus.BAD_REQUEST: ApiError,
    },
    url_name="create_article",
    summary="Create a new article",
)
@transaction.atomic()
def create_article_view(request: AuthenticatedApiRequest, payload: ArticleCreation):
    """Create an article either just with a link or with a link, a title and some content."""
    try:
        article_data = _get_article_data(payload)
    except (httpx.HTTPError, ArticleTooBigError, PydanticValidationError) as e:
        exception_detail = str(e) or e.__class__.__name__
        return HTTPStatus.BAD_REQUEST, {
            "detail": f"Failed to fetch article data: {exception_detail}"
        }

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


def _get_article_data(payload: ArticleCreation) -> ArticleData:
    if payload.has_data:
        return build_article_data_from_content(
            url=payload.url,
            title=payload.title,
            content=payload.content,
            content_type=payload.content_type,
        )
    return get_article_from_url(payload.url)


@reading_api_router.get(
    "/articles/",
    response={HTTPStatus.OK: list[OutArticleSchema]},
    url_name="list_articles",
    summary="List articles",
)
@paginate
def list_articles_view(request: AuthenticatedApiRequest, query: Query[ArticleFullTextSearchQuery]):
    return Article.objects.search(request.auth, query)


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
    title: CleanedString | SkipJsonSchema[NotSet] = NotSet(str)
    tags: (
        Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] | SkipJsonSchema[NotSet]
    ) = NotSet(tuple)
    read_at: datetime | SkipJsonSchema[NotSet] | None = NotSet(datetime.now)
    is_favorite: bool | SkipJsonSchema[NotSet] = NotSet(bool)
    is_for_later: bool | SkipJsonSchema[NotSet] = NotSet(bool)
    reading_time: int | SkipJsonSchema[NotSet] = NotSet(int)


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

    if not isinstance(payload.tags, NotSet):
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

    article.delete()

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


class ReadingListReorderPayload(Schema):
    order: dict[int, int]


@reading_api_router.post(
    "/lists/reorder/",
    url_name="reorder_reading_lists",
    summary="Reorder reading lists. Provide a mapping of reading list id to new order.",
    response={HTTPStatus.NO_CONTENT: None},
)
def reorder_reading_lists_view(
    request: AuthenticatedApiRequest, payload: ReadingListReorderPayload
):
    ReadingList.objects.reorder(request.auth, payload.order)

    return HTTPStatus.NO_CONTENT, None
