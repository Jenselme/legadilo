import logging
from asyncio import TaskGroup
from http import HTTPStatus
from ssl import SSLCertVerificationError
from typing import Any

from asgiref.sync import sync_to_async
from django.core.management.base import CommandParser
from httpx import AsyncClient, HTTPError, HTTPStatusError, Limits

from legadilo.feeds import constants
from legadilo.feeds.models import Feed, FeedUpdate
from legadilo.feeds.models.feed import FeedQuerySet
from legadilo.feeds.services.feed_parsing import get_feed_data
from legadilo.utils.command import AsyncCommand
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
            AsyncClient(
                limits=Limits(
                    max_connections=50, max_keepalive_connections=20, keepalive_expiry=5.0
                ),
                timeout=constants.HTTP_TIMEOUT_CMD_CTX,
                follow_redirects=True,
            ) as client,
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
        logger.debug("Updating feed %s", feed)
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
                await sync_to_async(Feed.objects.log_error)(feed, str(e))
            return
        except (HTTPError, SSLCertVerificationError) as e:
            logger.exception("Failed to update feed %s", feed)
            await sync_to_async(Feed.objects.log_error)(feed, str(e))
            return
        except Exception as e:
            logger.exception("Failed to update feed %s", feed)
            await sync_to_async(Feed.objects.log_error)(feed, str(e))

        await sync_to_async(Feed.objects.update_feed)(feed, feed_metadata)
        logger.debug("Updated feed %s", feed)
