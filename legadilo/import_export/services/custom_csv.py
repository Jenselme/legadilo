import csv
import json
import logging
import sys
from json import JSONDecodeError
from pathlib import Path
from ssl import SSLCertVerificationError
from urllib.parse import urlparse

import httpx
from asgiref.sync import async_to_sync, sync_to_async
from django.db import IntegrityError

from legadilo.feeds import constants as feeds_constants
from legadilo.feeds.models import Feed, FeedArticle, FeedCategory
from legadilo.feeds.services.feed_parsing import (
    FeedFileTooBigError,
    InvalidFeedFileError,
    NoFeedUrlFoundError,
    build_feed_data,
    get_feed_data,
)
from legadilo.import_export.services.exceptions import DataImportError
from legadilo.reading import constants as reading_constants
from legadilo.reading.models import Article
from legadilo.reading.services.article_fetching import build_article_data
from legadilo.users.models import User
from legadilo.utils.http import get_rss_async_client
from legadilo.utils.security import full_sanitize
from legadilo.utils.time import safe_datetime_parse
from legadilo.utils.validators import is_url_valid

logger = logging.getLogger(__name__)

csv.field_size_limit(sys.maxsize)


def import_custom_csv_file(user: User, path_to_file: str | Path) -> tuple[int, int, int]:
    nb_imported_articles = 0
    nb_imported_feeds = 0
    nb_imported_categories = 0
    with Path(path_to_file).open() as f:
        dict_reader = csv.DictReader(f)
        # This is used to cache feed values: the URL in the file may not be the latest available URL
        # To avoid making too many HTTP requests, we cache the result to reuse the latest URL as
        # soon as possible.
        feed_url_in_file_to_true_feed_url: dict[str, Feed] = {}
        for row in dict_reader:
            _check_keys_in_row(row)
            nb_articles, nb_feeds, nb_categories = _process_row(
                user, row, feed_url_in_file_to_true_feed_url
            )
            nb_imported_articles += nb_articles
            nb_imported_feeds += nb_feeds
            nb_imported_categories += nb_categories

    return nb_imported_articles, nb_imported_feeds, nb_imported_categories


def _check_keys_in_row(row: dict):
    if not {
        "category_id",
        "category_title",
        "feed_id",
        "feed_title",
        "feed_url",
        "feed_site_url",
        "article_id",
        "article_title",
        "article_link",
        "article_content",
        "article_date_published",
        "article_date_updated",
        "article_authors",
        "article_tags",
        "article_read_at",
        "article_is_favorite",
    }.issubset(row.keys()):
        raise DataImportError


def _process_row(user: User, row: dict, feed_url_in_file_to_true_feed_url: dict[str, Feed]):
    category = None
    created_category = False
    if row["category_title"]:
        category, created_category = _import_category(user, row)

    feed = None
    created_feed = False
    if row["feed_url"] and is_url_valid(row["feed_url"]) and is_url_valid(row["feed_site_url"]):
        feed, created_feed = async_to_sync(_import_feed)(
            user, category, row, feed_url_in_file_to_true_feed_url
        )

    created_article = False
    if row["article_link"] and is_url_valid(row["article_link"]):
        created_article = _import_article(user, feed, row)

    return (
        1 if created_article else 0,
        1 if created_feed else 0,
        1 if created_category else 0,
    )


def _import_category(user, row):
    return FeedCategory.objects.get_or_create(user=user, title=full_sanitize(row["category_title"]))


async def _import_feed(user, category, row, feed_url_in_file_to_true_feed_url):
    feed = feed_url_in_file_to_true_feed_url.get(row["feed_url"])

    if feed:
        return feed, False

    try:
        async with get_rss_async_client() as client:
            feed_data = await get_feed_data(row["feed_url"], client=client)

        feed, created = await sync_to_async(Feed.objects.create_from_metadata)(
            feed_data,
            user,
            refresh_delay=feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
            tags=[],
            category=category,
        )
        feed_url_in_file_to_true_feed_url[row["feed_url"]] = feed
        return feed, created
    except (
        httpx.HTTPError,
        NoFeedUrlFoundError,
        FeedFileTooBigError,
        InvalidFeedFileError,
        SSLCertVerificationError,
    ):
        logger.error(
            f"Failed to import feed {row["feed_url"]} Created with basic data and disabled."
        )
        feed_data = build_feed_data(
            feed_url=row["feed_url"],
            site_url=row["feed_site_url"],
            title=row["feed_title"],
            description="",
            feed_type=feeds_constants.SupportedFeedType.rss,
            etag="",
            last_modified=None,
            articles=[],
        )
        feed, created = await sync_to_async(Feed.objects.create_from_metadata)(
            feed_data,
            user=user,
            refresh_delay=feeds_constants.FeedRefreshDelays.DAILY_AT_NOON,
            tags=[],
            category=category,
        )
        if created:
            feed.disable("Failed to reach feed URL while importing an OPML file.")
            await feed.asave()

        feed_url_in_file_to_true_feed_url[row["feed_url"]] = feed
        return feed, created
    except IntegrityError:
        logger.info(f"You are already subscribed to {row["feed_url"]}")
        return None, False


def _import_article(user, feed, row):
    article_data = build_article_data(
        external_article_id=f"custom_csv:{row["article_id"]}",
        source_title=feed.title if feed else urlparse(row["article_link"]).netloc,
        title=row["article_title"],
        summary="",
        content=row["article_content"],
        authors=_safe_json_parse(row["article_authors"], []),
        contributors=[],
        tags=_safe_json_parse(row["article_tags"], []),
        link=row["article_link"],
        preview_picture_url="",
        preview_picture_alt="",
        published_at=safe_datetime_parse(row["article_date_published"]),
        updated_at=safe_datetime_parse(row["article_date_updated"]),
        language=row["article_lang"],
        read_at=safe_datetime_parse(row["article_read_at"]),
        is_favorite=_get_bool(row["article_is_favorite"]),
    )
    articles = Article.objects.update_or_create_from_articles_list(
        user=user,
        articles_data=[article_data],
        tags=[],
        source_type=reading_constants.ArticleSourceType.FEED
        if feed
        else reading_constants.ArticleSourceType.MANUAL,
    )

    if feed:
        FeedArticle.objects.get_or_create(feed=feed, article=articles[0])

    return True


def _get_bool(value):
    return value.lower() in {"true", "1", "t", "yes"}


def _safe_json_parse(data, default):
    try:
        return json.loads(data)
    except JSONDecodeError:
        return default
