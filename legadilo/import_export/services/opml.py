import logging
from asyncio import TaskGroup
from pathlib import Path

import httpx
from asgiref.sync import async_to_sync, sync_to_async
from defusedxml.ElementTree import parse
from django.db import IntegrityError

from legadilo.feeds import constants as feeds_constants
from legadilo.feeds.models import Feed, FeedCategory
from legadilo.feeds.services.feed_parsing import (
    FeedFileTooBigError,
    InvalidFeedFileError,
    get_feed_data,
)
from legadilo.users.models import User
from legadilo.utils.http import get_rss_async_client
from legadilo.utils.security import full_sanitize
from legadilo.utils.validators import is_url_valid

logger = logging.getLogger(__name__)


class OutlineElt:
    def __init__(self, node):
        self._node = node

    @property
    def children_outline(self):
        if not self.is_category:
            return []

        for outline_node in self._node.findall("outline"):
            yield OutlineElt(outline_node)

    @property
    def text(self):
        return self._node.get("text")

    @property
    def feed_url(self):
        return self._node.get("xmlUrl")

    @property
    def site_url(self):
        return self._node.get("htmlUrl")

    @property
    def is_category(self):
        return (
            self.feed_url is None
            and self.site_url is None
            and self.text
            and self.text not in {"tt-rss-labels", "tt-rss-prefs"}
        )

    @property
    def is_feed(self):
        return is_url_valid(self.feed_url) and is_url_valid(self.site_url) and self.text


def import_opml_file(user: User, path_to_file: str | Path) -> tuple[int, int]:
    with Path(path_to_file).open() as f:
        tree = parse(f)
        root = tree.getroot()
        return async_to_sync(_process_opml_data)(user, root)


async def _process_opml_data(user, root) -> tuple[int, int]:
    nb_imported_feeds = 0
    nb_imported_categories = 0
    body = root.find("body")
    if not body:
        return 0, 0

    tasks = []
    async with get_rss_async_client() as client, TaskGroup() as tg:
        for outline_node in body.findall("outline"):
            outline = OutlineElt(outline_node)
            tasks.append(tg.create_task(_process_outline(user, client, outline)))

    for task in tasks:
        task_result = task.result()
        nb_imported_feeds += task_result[0]
        nb_imported_categories += task_result[1]

    return nb_imported_feeds, nb_imported_categories


async def _process_outline(user, client, outline):
    nb_imported_categories = 0
    nb_imported_feeds = 0

    if outline.is_category:
        nb_imported_feeds, nb_imported_categories = await _process_category(user, client, outline)
    elif outline.is_feed:
        nb_imported_feeds = await _process_feed(user, client, outline)

    return nb_imported_feeds, nb_imported_categories


async def _process_category(user, client, outline):
    category, created = await FeedCategory.objects.aget_or_create(
        user=user, title=full_sanitize(outline.text)
    )
    nb_imported_categories = 0
    if created:
        logger.info(f"Imported category {category}")
        nb_imported_categories = 1
    nb_imported_feeds = 0
    for feed_outline in outline.children_outline:
        if not feed_outline.is_feed:
            continue

        nb_imported_feeds += await _process_feed(user, client, feed_outline, category)

    return nb_imported_feeds, nb_imported_categories


async def _process_feed(user, client, outline, category=None):
    nb_imported_feeds = 0
    try:
        logger.debug(f"Importing feed {outline.feed_url}")
        feed_data = await get_feed_data(outline.feed_url, client=client)
        await sync_to_async(Feed.objects.create_from_metadata)(
            feed_data,
            user,
            refresh_delay=feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
            tags=[],
            category=category,
        )
        nb_imported_feeds += 1
        logger.debug(f"Feed {outline.feed_url} imported successfully with all its metadata")
    except httpx.HTTPError:
        logger.exception(
            f"Failed to import feed {outline.feed_url}. Created with basic data and disabled."
        )
        await Feed.objects.aget_or_create(
            feed_url=outline.feed_url,
            user=user,
            defaults={
                "site_url": outline.site_url,
                "title": "",
                "refresh_delay": feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
                "description": "",
                "feed_type": feeds_constants.SupportedFeedType.rss,
                "category": category,
                "enabled": False,
                "disabled_reason": "Failed to reach feed URL while importing an OPML file.",
            },
        )
        nb_imported_feeds += 1
    except IntegrityError:
        logger.info(f"You are already subscribed to {outline.feed_url}")
    except (FeedFileTooBigError, InvalidFeedFileError):
        logger.exception("Failed to import the feed")

    return nb_imported_feeds
