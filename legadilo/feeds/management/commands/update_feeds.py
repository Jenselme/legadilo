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

import logging
from asyncio import TaskGroup
from http import HTTPStatus
from typing import Any

from asgiref.sync import sync_to_async
from django.core.management.base import CommandParser
from httpx import HTTPError, HTTPStatusError

from legadilo.feeds.models import Feed, FeedUpdate
from legadilo.feeds.models.feed import FeedQuerySet
from legadilo.feeds.services.feed_parsing import get_feed_data
from legadilo.utils.command import AsyncCommand
from legadilo.utils.exceptions import extract_debug_information, format_exception
from legadilo.utils.http import get_rss_async_client
from legadilo.utils.time import utcnow

logger = logging.getLogger(__name__)


class Command(AsyncCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--feed-ids",
            dest="feed_ids",
            default=None,
            nargs="+",
            type=int,
            help="Only update the feeds with the supplied ids.",
        )
        parser.add_argument(
            "--force",
            "-f",
            default=False,
            action="store_true",
            dest="force",
            help="Force an update even if it's not planned yet.",
        )
        parser.add_argument(
            "--user-ids",
            "-u",
            dest="user_ids",
            default=None,
            nargs="+",
            type=int,
            help="Only update the feeds for the supplied user ids.",
        )

    async def run(self, *args, **options):
        logger.info("Starting feed update")
        start_time = utcnow()
        async with (
            get_rss_async_client() as client,
            TaskGroup() as tg,
        ):
            async for feed in self._build_feed_qs(options):
                tg.create_task(self._update_feed(client, feed))

        duration = utcnow() - start_time
        logger.info("Completed feed update in %s", duration)

    def _build_feed_qs(self, options: dict[str, Any]) -> FeedQuerySet:
        feeds_qs = Feed.objects.get_queryset().select_related("user", "user__settings", "category")

        if options["feed_ids"]:
            feeds_qs = feeds_qs.only_with_ids(options["feed_ids"])

        if options["user_ids"]:
            feeds_qs = feeds_qs.only_with_ids(options["user_ids"])

        if options["force"]:  # noqa: SIM108 Use ternary operator
            feeds_qs = feeds_qs.only_enabled()
        else:
            feeds_qs = feeds_qs.for_update()

        return feeds_qs

    async def _update_feed(self, client, feed):
        logger.info("Updating feed %s", feed)
        feed_update = await FeedUpdate.objects.get_latest_success_for_feed(feed)
        try:
            feed_metadata = await get_feed_data(
                feed.feed_url,
                client=client,
                etag=feed_update.feed_etag if feed_update else None,
                last_modified=feed_update.feed_last_modified if feed_update else None,
            )
        except HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.NOT_MODIFIED:
                await sync_to_async(Feed.objects.log_not_modified)(feed)
            else:
                logger.exception("Failed to fetch feed %s", feed)
                await sync_to_async(Feed.objects.log_error)(
                    feed, format_exception(e), extract_debug_information(e)
                )
        except HTTPError as e:
            logger.exception("Failed to update feed %s", feed)
            await sync_to_async(Feed.objects.log_error)(
                feed, format_exception(e), extract_debug_information(e)
            )
        except Exception as e:
            logger.exception("Failed to update feed %s", feed)
            await sync_to_async(Feed.objects.log_error)(feed, format_exception(e))
        else:
            await sync_to_async(Feed.objects.update_feed)(feed, feed_metadata)
            logger.info("Updated feed %s", feed)
