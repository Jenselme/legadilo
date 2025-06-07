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

import logging
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
from http import HTTPStatus
from typing import Any

import httpx
from django.core.management.base import BaseCommand, CommandParser
from httpx import HTTPError, HTTPStatusError

from legadilo import constants
from legadilo.feeds.models import Feed, FeedUpdate
from legadilo.feeds.models.feed import FeedQuerySet
from legadilo.feeds.services.feed_parsing import get_feed_data
from legadilo.users.models import User
from legadilo.utils.exceptions import extract_debug_information, format_exception
from legadilo.utils.http_utils import get_rss_sync_client
from legadilo.utils.loggers import unlink_logger_from_sentry
from legadilo.utils.time_utils import utcnow

logger = logging.getLogger(__name__)

unlink_logger_from_sentry(logger)


class Command(BaseCommand):
    help = """Update all feeds.

    To do this, we check the feed file from its source, parse it and run debug code.
    """

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

    def handle(self, *args, **options):
        logger.info("Starting feed update")
        start_time = utcnow()
        futures = []

        with (
            get_rss_sync_client() as client,
            ThreadPoolExecutor(max_workers=constants.MAX_PARALLEL_CONNECTIONS) as executor,
        ):
            # Some updates (like the every morning ones) must run in the user TZ. So, we look at
            # users with feed and find the feeds to update based on their TZ from settings.
            for user in (
                User.objects.get_queryset()
                .with_feeds(options["user_ids"])
                .select_related("settings", "settings__timezone")
            ):
                for feed in self._build_feed_qs(user, options):
                    feed_update = FeedUpdate.objects.get_latest_success_for_feed_id(feed.id)
                    futures.append((
                        feed,
                        executor.submit(
                            self._fetch_feed_metadata,
                            client,
                            feed.id,
                            feed.feed_url,
                            feed_update.feed_etag if feed_update else None,
                            feed_update.feed_last_modified if feed_update else None,
                        ),
                    ))

        for feed, future in futures:
            self._update_feed_from_future(feed, future)

        duration = utcnow() - start_time
        logger.info("Completed feed update in %s", duration)

    def _build_feed_qs(self, user: User, options: dict[str, Any]) -> FeedQuerySet:
        feeds_qs = (
            Feed.objects.get_queryset()
            .select_related("user", "user__settings", "category")
            .filter(user=user)
        )

        if options["feed_ids"]:
            feeds_qs = feeds_qs.only_with_ids(options["feed_ids"])

        if options["force"]:  # noqa: SIM108 Use ternary operator
            feeds_qs = feeds_qs.only_enabled()
        else:
            feeds_qs = feeds_qs.for_update(user)

        return feeds_qs

    def _fetch_feed_metadata(
        self,
        client: httpx.Client,
        feed_id: int,
        feed_url: str,
        feed_etag: str | None,
        feed_last_modified: datetime | None,
    ):
        logger.info("Updating feed %s", feed_id)
        return get_feed_data(
            feed_url,
            client=client,
            etag=feed_etag,
            last_modified=feed_last_modified,
        )

    def _update_feed_from_future(self, feed: Feed, future: Future):
        try:
            feed_metadata = future.result()
        except HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.NOT_MODIFIED:
                Feed.objects.log_not_modified(feed)
            else:
                logger.exception("Failed to fetch feed %s", feed)
                Feed.objects.log_error(feed, format_exception(e), extract_debug_information(e))
        except HTTPError as e:
            logger.exception("Failed to update feed %s", feed)
            Feed.objects.log_error(feed, format_exception(e), extract_debug_information(e))
        except Exception as e:
            logger.exception("Failed to update feed %s", feed)
            Feed.objects.log_error(feed, format_exception(e))
        else:
            Feed.objects.update_feed(feed, feed_metadata)
            logger.info("Updated feed %s", feed)
