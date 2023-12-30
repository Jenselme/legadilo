import time
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import chain
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from feedparser import FeedParserDict
from feedparser import parse as parse_feed

from legadilo.utils.security import full_sanitize, sanitize_keep_safe_tags

from ..constants import SupportedFeedType


@dataclass(frozen=True)
class FeedArticle:
    article_feed_id: str
    title: str
    summary: str
    content: str
    authors: list[str]
    contributors: list[str]
    tags: list[str]
    link: str
    published_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FeedMetadata:
    feed_url: str
    site_url: str
    title: str
    description: str
    feed_type: SupportedFeedType
    articles: list[FeedArticle]


class NoFeedUrlFoundError(Exception):
    pass


class MultipleFeedFoundError(Exception):
    feed_urls: list[tuple[str, str]]

    def __init__(self, message, feed_urls):
        self.feed_urls = feed_urls
        super().__init__(message)


async def get_feed_metadata(url: str) -> FeedMetadata:
    """Find the feed medatadata from the supplied URL (either a feed or a page containing a link to a feed)."""
    async with httpx.AsyncClient() as client:
        parsed_feed, url_content = await _fetch_feed_and_raw_data(client, url)
        if not parsed_feed["version"]:
            url = find_feed_page_content(url_content)
            parsed_feed = await fetch_feed(client, url)

    return FeedMetadata(
        feed_url=url,
        site_url=_normalize_found_link(parsed_feed.feed.link),
        title=full_sanitize(parsed_feed.feed.title),
        description=full_sanitize(parsed_feed.feed.get("description", "")),
        feed_type=SupportedFeedType(parsed_feed.version),
        articles=parse_articles_in_feed(url, parsed_feed),
    )


async def _fetch_feed_and_raw_data(client: httpx.AsyncClient, url: str) -> tuple[FeedParserDict, str]:
    response = await client.get(url)
    feed_content = response.raise_for_status().text
    return parse_feed(feed_content), feed_content


async def fetch_feed(client: httpx.AsyncClient, url: str) -> FeedParserDict:
    parsed_feed, _ = await _fetch_feed_and_raw_data(client, url)
    return parsed_feed


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


def parse_articles_in_feed(feed_url: str, parsed_feed: FeedParserDict) -> list[FeedArticle]:
    return [
        FeedArticle(
            article_feed_id=full_sanitize(entry.id),
            title=full_sanitize(entry.title),
            summary=sanitize_keep_safe_tags(entry.summary),
            content=_get_article_content(entry),
            authors=_get_article_authors(entry),
            contributors=_get_article_contributors(entry),
            tags=_get_articles_tags(entry),
            link=_normalize_article_link(feed_url, entry.link),
            published_at=_get_article_datetime(entry.published_parsed),
            updated_at=_get_article_datetime(entry.updated_parsed),
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


def _normalize_article_link(feed_url, article_link):
    article_link = full_sanitize(article_link)

    if article_link.startswith("http://") or article_link.startswith("https://"):
        return article_link

    if article_link.startswith("//"):
        return f"https:{article_link}"

    parsed_feed_url = urlparse(feed_url)
    return urljoin(f"{parsed_feed_url.scheme}://{parsed_feed_url.netloc}", article_link)


def _get_article_datetime(time_value):
    return datetime.fromtimestamp(time.mktime(time_value), tz=UTC)
