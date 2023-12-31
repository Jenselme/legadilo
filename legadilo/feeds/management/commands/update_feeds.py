import logging
from asyncio import TaskGroup
from http import HTTPStatus

from django.core.management.base import CommandParser
from django.utils.translation import gettext_lazy as _
from httpx import AsyncClient, HTTPError, HTTPStatusError, Limits

from legadilo.feeds.models import Article, Feed, FeedUpdate
from legadilo.feeds.utils.feed_parsing import fetch_feed, parse_articles_in_feed, parse_feed_time
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
        async with AsyncClient(
            limits=Limits(max_connections=50, max_keepalive_connections=20, keepalive_expiry=5.0)
        ) as client, TaskGroup() as tg:
            async for feed in Feed.objects.all().only_feeds_to_update(options["feed_ids"]):
                tg.create_task(self._update_feed(client, feed))

    async def _update_feed(self, client, feed):
        logger.debug("Updating feed %s", feed)
        feed_update = await FeedUpdate.objects.get_latest_success_for_feed(feed)
        try:
            parsed_feed = await fetch_feed(
                client, feed.feed_url, etag=feed_update.feed_etag, last_modified=feed_update.feed_last_modified
            )
        except HTTPStatusError as e:
            if e.response.status_code == HTTPStatus.NOT_MODIFIED:
                logger.debug("Feed hasn't changed, nothing to do")
            else:
                logger.exception("Failed to fetch feed %s", feed)
                await self._handle_error(feed, str(e))
            return
        except HTTPError as e:
            logger.exception("Failed to update feed %s", feed)
            await self._handle_error(feed, str(e))
            return

        articles = parse_articles_in_feed(feed.feed_url, parsed_feed)
        logger.debug("Fetched feed file for feed %s", feed)
        await Article.objects.update_or_create_from_articles_list(articles, feed.id)
        await FeedUpdate.objects.acreate(
            success=True,
            feed_etag=parsed_feed.get("etag", ""),
            feed_last_modified=parse_feed_time(parsed_feed.get("modified_parsed")),
            feed=feed,
        )
        logger.debug("Updated feed %s", feed)

    async def _handle_error(self, feed, error_message):
        await FeedUpdate.objects.acreate(
            success=False,
            error_message=error_message,
            feed=feed,
        )
        if await FeedUpdate.objects.must_disable_feed(feed):
            feed.disable(_("We failed too many times to fetch the feed"))
            await feed.asave()
