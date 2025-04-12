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

from datetime import datetime
from http import HTTPStatus
from operator import xor
from typing import Annotated, Self

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from ninja import ModelSchema, Query, Router, Schema
from ninja.errors import ValidationError as NinjaValidationError
from ninja.pagination import paginate
from pydantic import Field, model_validator

from config import settings
from legadilo.feeds import constants
from legadilo.feeds.models import Feed, FeedCategory, FeedTag
from legadilo.feeds.services.feed_parsing import (
    FeedFileTooBigError,
    MultipleFeedFoundError,
    NoFeedUrlFoundError,
    get_feed_data,
)
from legadilo.reading.api import OutTagSchema
from legadilo.reading.models import Tag
from legadilo.users.models import User
from legadilo.users.user_types import AuthenticatedApiRequest
from legadilo.utils.api import FIELD_UNSET, ApiError, update_model_from_schema
from legadilo.utils.http_utils import get_rss_sync_client
from legadilo.utils.validators import (
    CleanedString,
    FullSanitizeValidator,
    ValidUrlValidator,
    remove_falsy_items,
)

feeds_api_router = Router(tags=["feeds"])


class OutFeedCategorySchema(ModelSchema):
    class Meta:
        model = FeedCategory
        exclude = ("user", "created_at", "updated_at")


class OutFeedSchema(ModelSchema):
    category: OutFeedCategorySchema | None
    tags: list[OutTagSchema]
    details_url: str

    @staticmethod
    def resolve_details_url(obj, context) -> str:
        url = reverse("feeds:feed_articles", kwargs={"feed_id": obj.id, "feed_slug": obj.slug})
        return context["request"].build_absolute_uri(url)

    class Meta:
        model = Feed
        exclude = ("user", "created_at", "updated_at", "articles")


class FeedsSearchQuery(Schema):
    feed_urls: list[Annotated[str, ValidUrlValidator]] = Field(default_factory=list)
    enabled: bool | None = None


@feeds_api_router.get(
    "", response=list[OutFeedSchema], url_name="list_feeds", summary="List all you feeds"
)
@paginate
def list_feeds_view(request: AuthenticatedApiRequest, query: Query[FeedsSearchQuery]):
    qs = Feed.objects.get_queryset().for_user(request.auth).for_api()
    if query.feed_urls:
        qs = qs.for_feed_urls_search(query.feed_urls)

    if query.enabled is not None:
        qs = qs.for_status_search(enabled=query.enabled)

    return qs


class FeedSubscription(Schema):
    feed_url: Annotated[str, ValidUrlValidator]
    refresh_delay: constants.FeedRefreshDelays = constants.FeedRefreshDelays.DAILY_AT_NOON
    article_retention_time: int = 0
    category_id: int | None = None
    tags: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()
    open_original_url_by_default: bool = False


@feeds_api_router.post(
    "",
    response={
        HTTPStatus.CREATED: OutFeedSchema,
        HTTPStatus.ALREADY_REPORTED: OutFeedSchema,
        HTTPStatus.NOT_ACCEPTABLE: ApiError,
    },
    url_name="subscribe_to_feed",
    summary="Subscribe to feed from its link",
)
def subscribe_to_feed_view(request: AuthenticatedApiRequest, payload: FeedSubscription):
    """Many parameters of the feed can be customized directly at creation."""
    category = _get_category(request.auth, payload.category_id)

    try:
        with get_rss_sync_client() as client:
            feed_medata = get_feed_data(payload.feed_url, client=client)
        tags = Tag.objects.get_or_create_from_list(request.auth, payload.tags)
        feed, created = Feed.objects.create_from_metadata(
            feed_medata,
            request.auth,
            payload.refresh_delay,
            payload.article_retention_time,
            tags,
            category,
            open_original_url_by_default=payload.open_original_url_by_default,
        )
    except (NoFeedUrlFoundError, MultipleFeedFoundError):
        return HTTPStatus.NOT_ACCEPTABLE, {
            "detail": "We failed to find a feed at the supplied URL."
        }
    except FeedFileTooBigError:
        return HTTPStatus.NOT_ACCEPTABLE, {"detail": "The feed is too big."}
    except Exception:  # noqa: BLE001 Do not catch blind exception: `Exception`
        # That's the catch of weird validation, parsing and network errors.
        return HTTPStatus.NOT_ACCEPTABLE, {
            "detail": "We failed to access or parse the feed you supplied. Please make sure it is "
            "accessible and valid."
        }

    status = HTTPStatus.CREATED if created else HTTPStatus.ALREADY_REPORTED

    return status, Feed.objects.get_queryset().for_api().get(id=feed.id)


def _get_category(user: User, category_id: int | None) -> FeedCategory | None:
    if category_id is None:
        return None

    try:
        return FeedCategory.objects.get(id=category_id, user=user)
    except FeedCategory.DoesNotExist as e:
        raise NinjaValidationError([
            {"category_id": f"We failed to find the category with id: {category_id}"}
        ]) from e


@feeds_api_router.get(
    "/{int:feed_id}/",
    response=OutFeedSchema,
    url_name="get_feed",
    summary="View the details of a specific feed",
)
def get_feed_view(request: AuthenticatedApiRequest, feed_id: int):
    return get_object_or_404(Feed.objects.get_queryset().for_api(), id=feed_id, user=request.auth)


class FeedUpdate(Schema):
    disabled_reason: Annotated[str, FullSanitizeValidator] | None = FIELD_UNSET
    disabled_at: datetime | None = FIELD_UNSET
    category_id: int | None = FIELD_UNSET
    tags: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = FIELD_UNSET
    refresh_delay: constants.FeedRefreshDelays = FIELD_UNSET
    article_retention_time: int = FIELD_UNSET
    open_original_url_by_default: bool = FIELD_UNSET

    @model_validator(mode="after")
    def check_disabled(self) -> Self:
        if xor(self.disabled_reason is FIELD_UNSET, self.disabled_at is FIELD_UNSET) or xor(
            self.disabled_reason is None, self.disabled_at is None
        ):
            raise ValueError(
                "You must supply none of disabled_reason and disabled_at or both of them"
            )

        if self.disabled_reason is None:
            self.disabled_reason = ""

        return self


@feeds_api_router.patch(
    "/{int:feed_id}/", response=OutFeedSchema, url_name="update_feed", summary="Update a feed"
)
def update_feed_view(
    request: AuthenticatedApiRequest,
    feed_id: int,
    payload: FeedUpdate,
):
    qs = Feed.objects.get_queryset().select_related("category")
    feed = get_object_or_404(qs, id=feed_id, user=request.auth)

    if payload.tags is not FIELD_UNSET:
        _update_feed_tags(request.auth, feed, payload.tags)

    # We must refresh to update generated fields & tags.
    update_model_from_schema(feed, payload, excluded_fields={"tags"})

    return Feed.objects.get_queryset().for_api().get(id=feed_id)


def _update_feed_tags(user: User, feed: Feed, new_tags: tuple[str, ...]):
    tags = Tag.objects.get_or_create_from_list(user, new_tags)
    FeedTag.objects.associate_feed_with_tag_slugs(
        feed, [tag.slug for tag in tags], clear_existing=True
    )


@feeds_api_router.delete(
    "/{int:feed_id}/",
    response={HTTPStatus.NO_CONTENT: None},
    url_name="delete_feed",
    summary="Delete a feed",
)
def delete_feed_view(request: AuthenticatedApiRequest, feed_id: int):
    feed = get_object_or_404(Feed, id=feed_id, user=request.auth)

    feed.delete()

    return HTTPStatus.NO_CONTENT, None


@feeds_api_router.get(
    "/categories/",
    response=list[OutFeedCategorySchema],
    url_name="list_feed_categories",
    summary="List all your feed categories",
)
# Let's get all categories.
@paginate(page_size=settings.NINJA_PAGINATION_MAX_LIMIT * 4)
def list_categories_view(request: AuthenticatedApiRequest):
    return FeedCategory.objects.get_queryset().for_user(request.auth)


class FeedCategoryPayload(Schema):
    title: str


@feeds_api_router.post(
    "/categories/",
    response={HTTPStatus.CREATED: OutFeedCategorySchema, HTTPStatus.CONFLICT: ApiError},
    url_name="create_feed_category",
    summary="Create a feed category",
)
def create_category_view(request: AuthenticatedApiRequest, payload: FeedCategoryPayload):
    return _create_feed_category(request.auth, payload)


@transaction.atomic()
def _create_feed_category(user: User, payload: FeedCategoryPayload):
    # We must wrap it in a transaction to have the proper error messages and SQL queries in tests.
    try:
        category = FeedCategory.objects.create(title=payload.title, user=user)
    except IntegrityError:
        return HTTPStatus.CONFLICT, {"detail": "A category with this title already exists."}

    return HTTPStatus.CREATED, category


@feeds_api_router.get(
    "/categories/{int:category_id}",
    response=OutFeedCategorySchema,
    url_name="get_feed_category",
    summary="View a specific feed category",
)
def get_category_view(request: AuthenticatedApiRequest, category_id: int):
    return get_object_or_404(FeedCategory, id=category_id, user=request.auth)


@feeds_api_router.patch(
    "/categories/{int:category_id}/",
    response=OutFeedCategorySchema,
    url_name="update_feed_category",
    summary="Update a feed category",
)
def update_category_view(
    request: AuthenticatedApiRequest,
    category_id: int,
    payload: FeedCategoryPayload,
) -> FeedCategory:
    category = get_object_or_404(FeedCategory, id=category_id, user=request.auth)

    update_model_from_schema(category, payload)

    return category


@feeds_api_router.delete(
    "/categories/{int:category_id}/",
    url_name="delete_feed_category",
    response={HTTPStatus.NO_CONTENT: None},
    summary="Delete a feed category",
)
def delete_category_view(request: AuthenticatedApiRequest, category_id: int):
    category = get_object_or_404(FeedCategory, id=category_id, user=request.auth)

    category.delete()

    return HTTPStatus.NO_CONTENT, None
