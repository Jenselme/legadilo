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
from django.db import IntegrityError, transaction
from django.shortcuts import aget_object_or_404
from ninja import ModelSchema, PatchDict, Router, Schema
from ninja.errors import ValidationError as NinjaValidationError
from ninja.pagination import paginate
from pydantic import model_validator

from legadilo.feeds import constants
from legadilo.feeds.models import Feed, FeedCategory, FeedTag
from legadilo.feeds.services.feed_parsing import (
    FeedFileTooBigError,
    MultipleFeedFoundError,
    NoFeedUrlFoundError,
    get_feed_data,
)
from legadilo.reading.models import Tag
from legadilo.users.models import User
from legadilo.users.user_types import AuthenticatedApiRequest
from legadilo.utils.api import ApiError, update_model_from_patch_dict
from legadilo.utils.http_utils import get_rss_async_client
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

    class Meta:
        model = Feed
        exclude = ("user", "created_at", "updated_at", "articles")


@feeds_api_router.get(
    "", response=list[OutFeedSchema], url_name="list_feeds", summary="List all you feeds"
)
@paginate
async def list_feeds_view(request: AuthenticatedApiRequest):  # noqa: RUF029 paginate is async!
    return Feed.objects.get_queryset().for_user(request.auth).select_related("category")


class FeedSubscription(Schema):
    feed_url: Annotated[str, ValidUrlValidator]
    refresh_delay: constants.FeedRefreshDelays = constants.FeedRefreshDelays.DAILY_AT_NOON
    article_retention_time: int = 0
    category_id: int | None = None
    tags: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()
    open_original_link_by_default: bool = False


@feeds_api_router.post(
    "",
    response={
        HTTPStatus.CREATED: OutFeedSchema,
        HTTPStatus.CONFLICT: ApiError,
        HTTPStatus.NOT_ACCEPTABLE: ApiError,
    },
    url_name="subscribe_to_feed",
    summary="Subscribe to feed from its link",
)
async def subscribe_to_feed_view(request: AuthenticatedApiRequest, payload: FeedSubscription):
    """Many parameters of the feed can be customized directly at creation."""
    category = await _get_category(request.auth, payload.category_id)

    try:
        async with get_rss_async_client() as client:
            feed_medata = await get_feed_data(payload.feed_url, client=client)
        tags = await sync_to_async(Tag.objects.get_or_create_from_list)(request.auth, payload.tags)
        feed, created = await sync_to_async(Feed.objects.create_from_metadata)(
            feed_medata,
            request.auth,
            payload.refresh_delay,
            payload.article_retention_time,
            tags,
            category,
            open_original_link_by_default=payload.open_original_link_by_default,
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

    if not created:
        return HTTPStatus.CONFLICT, {"detail": "You are already subscribed to this feed"}

    return HTTPStatus.CREATED, feed


async def _get_category(user: User, category_id: int | None) -> FeedCategory | None:
    if category_id is None:
        return None

    try:
        return await FeedCategory.objects.aget(id=category_id, user=user)
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
async def get_feed_view(request: AuthenticatedApiRequest, feed_id: int):
    return await aget_object_or_404(
        Feed.objects.get_queryset().select_related("category"), id=feed_id, user=request.auth
    )


class FeedUpdate(Schema):
    disabled_reason: Annotated[str, FullSanitizeValidator] = ""
    disabled_at: datetime | None = None
    category_id: int | None = None
    tags: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()
    refresh_delay: constants.FeedRefreshDelays
    article_retention_time: int
    open_original_link_by_default: bool

    @model_validator(mode="after")
    def check_disabled(self) -> Self:
        if xor(bool(self.disabled_reason), bool(self.disabled_at)):
            raise ValueError(
                "You must supply none of disabled_reason and disabled_at or both of them"
            )

        if self.disabled_reason is None:
            self.disabled_reason = ""

        return self


@feeds_api_router.patch(
    "/{int:feed_id}/", response=OutFeedSchema, url_name="update_feed", summary="Update a feed"
)
async def update_feed_view(
    request: AuthenticatedApiRequest,
    feed_id: int,
    payload: PatchDict[FeedUpdate],  # type: ignore[type-arg]
):
    qs = Feed.objects.get_queryset().select_related("category")
    feed = await aget_object_or_404(qs, id=feed_id, user=request.auth)

    if (tags := payload.pop("tags", None)) is not None:
        await _update_feed_tags(request.auth, feed, tags)

    # We must refresh to update generated fields & tags.
    await update_model_from_patch_dict(feed, payload, must_refresh=True, refresh_qs=qs)

    return feed


async def _update_feed_tags(user: User, feed: Feed, new_tags: tuple[str, ...]):
    tags = await sync_to_async(Tag.objects.get_or_create_from_list)(user, new_tags)
    await sync_to_async(FeedTag.objects.associate_feed_with_tag_slugs)(
        feed, [tag.slug for tag in tags], clear_existing=True
    )


@feeds_api_router.delete(
    "/{int:feed_id}/",
    response={HTTPStatus.NO_CONTENT: None},
    url_name="delete_feed",
    summary="Delete a feed",
)
async def delete_feed_view(request: AuthenticatedApiRequest, feed_id: int):
    feed = await aget_object_or_404(Feed, id=feed_id, user=request.auth)

    await feed.adelete()

    return HTTPStatus.NO_CONTENT, None


@feeds_api_router.get(
    "/categories/",
    response=list[OutFeedCategorySchema],
    url_name="list_feed_categories",
    summary="List all your feed categories",
)
@paginate
async def list_categories_view(request: AuthenticatedApiRequest):  # noqa: RUF029 paginate is async!
    return FeedCategory.objects.get_queryset().for_user(request.auth)


class FeedCategoryPayload(Schema):
    title: str


@feeds_api_router.post(
    "/categories/",
    response={HTTPStatus.CREATED: OutFeedCategorySchema, HTTPStatus.CONFLICT: ApiError},
    url_name="create_feed_category",
    summary="Create a feed category",
)
async def create_category_view(request: AuthenticatedApiRequest, payload: FeedCategoryPayload):
    return await sync_to_async(_create_feed_category)(request.auth, payload)


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
async def get_category_view(request: AuthenticatedApiRequest, category_id: int):
    return await aget_object_or_404(FeedCategory, id=category_id, user=request.auth)


@feeds_api_router.patch(
    "/categories/{int:category_id}/",
    response=OutFeedCategorySchema,
    url_name="update_feed_category",
    summary="Update a feed category",
)
async def update_category_view(
    request: AuthenticatedApiRequest,
    category_id: int,
    payload: PatchDict[FeedCategoryPayload],  # type: ignore[type-arg]
) -> FeedCategory:
    category = await aget_object_or_404(FeedCategory, id=category_id, user=request.auth)

    await update_model_from_patch_dict(category, payload)

    return category


@feeds_api_router.delete(
    "/categories/{int:category_id}/",
    url_name="delete_feed_category",
    response={HTTPStatus.NO_CONTENT: None},
    summary="Delete a feed category",
)
async def delete_category_view(request: AuthenticatedApiRequest, category_id: int):
    category = await aget_object_or_404(FeedCategory, id=category_id, user=request.auth)

    await category.adelete()

    return HTTPStatus.NO_CONTENT, None
