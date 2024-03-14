import logging
from asyncio import TaskGroup
from http import HTTPStatus

from asgiref.sync import sync_to_async
from django.core.management.base import CommandParser
from httpx import AsyncClient, HTTPError, HTTPStatusError, Limits

from legadilo.feeds import constants
from legadilo.feeds.models import Feed, FeedUpdate
from legadilo.feeds.utils.feed_parsing import get_feed_metadata
from legadilo.utils.command import AsyncCommand

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

    async def run(self, *args, **options):
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
            async for feed in Feed.objects.get_queryset().only_feeds_to_update(options["feed_ids"]):
                tg.create_task(self._update_feed(client, feed))

    async def _update_feed(self, client, feed):
        logger.debug("Updating feed %s", feed)
        feed_update = await FeedUpdate.objects.get_latest_success_for_feed(feed)
        try:
            feed_metadata = await get_feed_metadata(
                feed.feed_url,
                client=client,
                etag=feed_update.feed_etag,
                last_modified=feed_update.feed_last_modified,
            )
        except HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.NOT_MODIFIED:
                logger.debug("Feed hasn't changed, nothing to do")
            else:
                logger.exception("Failed to fetch feed %s", feed)
                await sync_to_async(Feed.objects.disable)(feed, str(e))
            return
        except HTTPError as e:
            logger.exception("Failed to update feed %s", feed)
            await sync_to_async(Feed.objects.disable)(feed, str(e))
            return

        await sync_to_async(Feed.objects.update_feed)(feed, feed_metadata)
        logger.debug("Updated feed %s", feed)
