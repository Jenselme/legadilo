import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import chain

import httpx
from bs4 import BeautifulSoup
from feedparser import FeedParserDict
from feedparser import parse as parse_feed

from legadilo.utils.security import full_sanitize, sanitize_keep_safe_tags

from ...utils.time import dt_to_http_date
from ...utils.validators import normalize_url
from .. import constants
from .article_fetching import ArticleData


@dataclass(frozen=True)
class FeedMetadata:
    feed_url: str
    site_url: str
    title: str
    description: str
    feed_type: constants.SupportedFeedType
    etag: str
    last_modified: datetime | None
    articles: list[ArticleData]


class NoFeedUrlFoundError(Exception):
    pass


class MultipleFeedFoundError(Exception):
    feed_urls: list[tuple[str, str]]

    def __init__(self, message, feed_urls):
        self.feed_urls = feed_urls
        super().__init__(message)


class FeedFileTooBigError(Exception):
    pass


class InvalidFeedFileError(Exception):
    pass


class InvalidFeedArticleError(InvalidFeedFileError):
    pass


async def get_feed_metadata(
    url: str,
    *,
    client: httpx.AsyncClient,
    etag: str | None = None,
    last_modified: datetime | None = None,
) -> FeedMetadata:
    """Find the feed metadata from the supplied URL (either a feed or a page containing a link to
    a feed).
    """

    parsed_feed, url_content, resolved_url = await _fetch_feed_and_raw_data(client, url)
    if not parsed_feed["version"]:
        url = find_feed_page_content(url_content)
        parsed_feed, resolved_url = await _fetch_feed(
            client, url, etag=etag, last_modified=last_modified
        )

    feed_title = full_sanitize(parsed_feed.feed.title)
    return FeedMetadata(
        feed_url=str(resolved_url),
        site_url=_normalize_found_link(parsed_feed.feed.link),
        title=feed_title,
        description=full_sanitize(parsed_feed.feed.get("description", "")),
        feed_type=constants.SupportedFeedType(parsed_feed.version),
        articles=parse_articles_in_feed(url, feed_title, parsed_feed),
        etag=parsed_feed.get("etag", ""),
        last_modified=_parse_feed_time(parsed_feed.get("modified_parsed")),
    )


async def _fetch_feed_and_raw_data(
    client: httpx.AsyncClient,
    url: str,
    etag: str | None = None,
    last_modified: datetime | None = None,
) -> tuple[FeedParserDict, str, httpx.URL]:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = dt_to_http_date(last_modified)

    response = await client.get(url, headers=headers)
    raw_feed_content = response.raise_for_status().content
    if sys.getsizeof(raw_feed_content) > constants.MAX_FEED_FILE_SIZE:
        raise FeedFileTooBigError

    feed_content = raw_feed_content.decode(response.encoding or "utf-8")
    return parse_feed(feed_content), feed_content, response.url


async def _fetch_feed(
    client: httpx.AsyncClient, url: str, *, etag: str | None, last_modified: datetime | None
) -> tuple[FeedParserDict, httpx.URL]:
    parsed_feed, _, resolved_url = await _fetch_feed_and_raw_data(
        client, url, etag=etag, last_modified=last_modified
    )
    return parsed_feed, resolved_url


def find_feed_page_content(page_content: str) -> str:
    soup = BeautifulSoup(page_content, "html.parser")
    atom_feeds = soup.find_all("link", {"type": "application/atom+xml"})
    rss_feeds = soup.find_all("link", {"type": "application/rss+xml"})
    feed_urls = []
    seen_feed_urls = set()
    for feed in chain(atom_feeds, rss_feeds):
        if not (href := feed.get("href")):
            continue

        normalized_link = _normalize_found_link(href)
        if normalized_link in seen_feed_urls:
            continue

        feed_urls.append((normalized_link, feed.get("title") or normalized_link))
        seen_feed_urls.add(normalized_link)

    if len(feed_urls) == 0:
        raise NoFeedUrlFoundError
    if len(feed_urls) > 1:
        raise MultipleFeedFoundError("Found multiple feeds URLs", feed_urls=feed_urls)

    return feed_urls[0][0]


def _normalize_found_link(link: str):
    if link.startswith("//"):
        link = f"https:{link}"

    return link


def parse_articles_in_feed(
    feed_url: str, feed_title: str, parsed_feed: FeedParserDict
) -> list[ArticleData]:
    return [
        ArticleData(
            external_article_id=full_sanitize(entry.id),
            title=full_sanitize(entry.title),
            summary=sanitize_keep_safe_tags(entry.summary),
            content=_get_article_content(entry),
            authors=_get_article_authors(entry),
            contributors=_get_article_contributors(entry),
            tags=_get_articles_tags(entry),
            link=_get_article_link(feed_url, entry),
            published_at=_feed_time_to_datetime(entry.published_parsed),
            updated_at=_feed_time_to_datetime(entry.updated_parsed),
            source_title=feed_title,
        )
        for entry in parsed_feed.entries
    ]


def _get_article_authors(entry):
    if authors := entry.get("authors", []):
        return [full_sanitize(author["name"]) for author in authors]

    if author := entry.get("author", ""):
        return [full_sanitize(author)]

    return []


def _get_article_contributors(entry):
    return [full_sanitize(contributor["name"]) for contributor in entry.get("contributors", [])]


def _get_article_content(entry):
    for content_entry in entry.get("content", []):
        if content_entry["type"] == "text/html":
            return sanitize_keep_safe_tags(content_entry["value"])

    return ""


def _get_articles_tags(entry):
    if tags := entry.get("tags", []):
        return [full_sanitize(tag["term"]) for tag in tags]

    if category := entry.get("category"):
        return [category]

    return []


def _get_article_link(feed_url, entry):
    try:
        return normalize_url(feed_url, entry.link)
    except ValueError as e:
        raise InvalidFeedArticleError from e


def _feed_time_to_datetime(time_value: time.struct_time):
    if not time_value:
        return None

    return datetime.fromtimestamp(time.mktime(time_value), tz=UTC)


def _parse_feed_time(time_value: time.struct_time | None) -> datetime | None:
    if not time_value:
        return None

    return _feed_time_to_datetime(time_value)
