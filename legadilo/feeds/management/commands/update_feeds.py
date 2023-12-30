import logging
from asyncio import TaskGroup

from django.core.management.base import CommandParser
from httpx import AsyncClient, HTTPError, Limits

from legadilo.feeds.models import Article, Feed
from legadilo.feeds.utils.feed_parsing import fetch_feed, parse_articles_in_feed
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
        feeds = Feed.objects.all()
        if options["feed_ids"]:
            feeds = feeds.filter(id__in=options["feed_ids"])

        async with AsyncClient(
            limits=Limits(max_connections=50, max_keepalive_connections=20, keepalive_expiry=5.0)
        ) as client, TaskGroup() as tg:
            async for feed in feeds:
                tg.create_task(self._update_feed(client, feed))

    async def _update_feed(self, client, feed):
        logger.debug("Updating feed %s", feed)
        try:
            parsed_feed = await fetch_feed(client, feed.feed_url)
        except HTTPError:
            logger.exception("Failed to update feed %s", feed)
            return

        articles = parse_articles_in_feed(feed.feed_url, parsed_feed)
        logger.debug("Fetched feed file for feed %s", feed)
        await Article.objects.update_or_create_from_articles_list(articles, feed.id)
        logger.debug("Updated feed %s", feed)
