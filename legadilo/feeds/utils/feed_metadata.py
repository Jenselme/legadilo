from dataclasses import dataclass
from itertools import chain

import httpx
from bs4 import BeautifulSoup
from feedparser import parse as parse_feed

from legadilo.utils.security import full_sanitize

from ..constants import SupportedFeedType


@dataclass(frozen=True)
class FeedMetadata:
    feed_url: str
    site_url: str
    title: str
    description: str
    feed_type: SupportedFeedType


class NoFeedUrlFoundError(Exception):
    pass


class MultipleFeedFoundError(Exception):
    feed_urls: list[tuple[str, str]]

    def __init__(self, message, feed_urls):
        self.feed_urls = feed_urls
        super().__init__(message)


async def get_feed_metadata(url: str) -> FeedMetadata:
    """Find the feed medatadata from the supplied URL (either a feed or a page containing a link to a feed)."""
    url_content = await _aget(url)
    parsed_feed = parse_feed(url_content)
    if not parsed_feed["version"]:
        url = find_feed_page_content(url_content)
        url_content = await _aget(url)
        parsed_feed = parse_feed(url_content)

    return FeedMetadata(
        feed_url=url,
        site_url=_normalize_found_link(parsed_feed.feed.link),
        title=full_sanitize(parsed_feed.feed.title),
        description=full_sanitize(parsed_feed.feed.get("description", "")),
        feed_type=SupportedFeedType(parsed_feed.version),
    )


async def _aget(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.raise_for_status().text


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
