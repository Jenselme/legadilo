# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import re
import sys
import time
from datetime import UTC, datetime
from html import unescape
from itertools import chain
from typing import Annotated
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup
from feedparser import FeedParserDict
from feedparser import parse as parse_feed
from pydantic import BaseModel as BaseSchema

from legadilo.reading.services.article_fetching import (
    ArticleData,
    parse_tags_list,
)

from ...utils.time_utils import dt_to_http_date
from ...utils.validators import (
    CleanedString,
    ValidUrlValidator,
    default_frozen_model_config,
    is_url_valid,
    normalize_url,
    truncate,
)
from .. import constants

logger = logging.getLogger(__name__)


class FeedData(BaseSchema):
    model_config = default_frozen_model_config

    feed_url: Annotated[str, ValidUrlValidator]
    site_url: Annotated[str, ValidUrlValidator]
    title: Annotated[CleanedString, truncate(constants.FEED_TITLE_MAX_LENGTH)]
    description: CleanedString
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


class FailedToParseArticleError(InvalidFeedFileError):
    pass


def get_feed_data(
    url: str,
    *,
    client: httpx.Client,
    etag: str | None = None,
    last_modified: datetime | None = None,
) -> FeedData:
    """Find the feed data from the supplied URL.

    It's either a feed or a page containing a link to a feed.
    """
    if _is_youtube_url(url):
        url = _find_youtube_rss_feed_url(url)

    parsed_feed, url_content, resolved_url = _fetch_feed_and_raw_data(client, url)
    if not parsed_feed.get("version"):
        url = _find_feed_page_content(url_content)
        parsed_feed, resolved_url = _fetch_feed(client, url, etag=etag, last_modified=last_modified)

    return build_feed_data_from_parsed_feed(parsed_feed, str(resolved_url))


def _find_youtube_rss_feed_url(url: str) -> str:
    is_youtube_feed = (
        re.match(
            r"https://[^/]+/feeds/videos.xml\?(channel_id|playlist_id)=.+",
            url,
            re.IGNORECASE,
        )
        is not None
    )
    if is_youtube_feed:
        return url

    if match_channel_with_id := re.match(
        r"https://[^/]+/channel/(?P<channel_id>.+)", url, re.IGNORECASE
    ):
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={match_channel_with_id.group('channel_id')}"

    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    if params.get("list"):
        return f"https://www.youtube.com/feeds/videos.xml?playlist_id={params['list'][0]}"

    # Can't handle it. Let's let it through.
    return url


def build_feed_data_from_parsed_feed(parsed_feed: FeedParserDict, resolved_url: str) -> FeedData:
    feed_title = parsed_feed.feed.get("title", "")

    return FeedData(
        feed_url=resolved_url,
        site_url=_get_feed_site_url(parsed_feed.feed.get("link"), resolved_url),
        title=feed_title,
        description=parsed_feed.feed.get("description", ""),
        feed_type=constants.SupportedFeedType(parsed_feed.version),
        articles=_parse_articles_in_feed(resolved_url, feed_title, parsed_feed),
        etag=parsed_feed.get("etag", ""),
        last_modified=_parse_feed_time(parsed_feed.get("modified_parsed")),
    )


def _fetch_feed_and_raw_data(
    client: httpx.Client,
    url: str,
    etag: str | None = None,
    last_modified: datetime | None = None,
) -> tuple[FeedParserDict, str, httpx.URL]:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = dt_to_http_date(last_modified)

    response = client.get(url, headers=headers, follow_redirects=True)
    raw_feed_content = response.raise_for_status().content
    if sys.getsizeof(raw_feed_content) > constants.MAX_FEED_FILE_SIZE:
        raise FeedFileTooBigError

    feed_content = raw_feed_content.decode(response.encoding or "utf-8")
    return (
        parse_feed(feed_content, resolve_relative_uris=True, sanitize_html=False),
        feed_content,
        response.url,
    )


def _fetch_feed(
    client: httpx.Client, url: str, *, etag: str | None, last_modified: datetime | None
) -> tuple[FeedParserDict, httpx.URL]:
    parsed_feed, _, resolved_url = _fetch_feed_and_raw_data(
        client, url, etag=etag, last_modified=last_modified
    )
    return parsed_feed, resolved_url


def _find_feed_page_content(page_content: str) -> str:
    soup = BeautifulSoup(page_content, "html.parser")
    atom_feeds = soup.find_all("link", {"type": "application/atom+xml"})
    rss_feeds = soup.find_all("link", {"type": "application/rss+xml"})
    feed_urls = []
    seen_feed_urls = set()
    for feed in chain(atom_feeds, rss_feeds):
        if not (href := feed.get("href")):
            continue

        normalized_url = _normalize_found_url(href)
        if normalized_url in seen_feed_urls:
            continue

        feed_urls.append((normalized_url, feed.get("title") or normalized_url))
        seen_feed_urls.add(normalized_url)

    if len(feed_urls) == 0:
        raise NoFeedUrlFoundError
    if len(feed_urls) > 1:
        raise MultipleFeedFoundError("Found multiple feeds URLs", feed_urls=feed_urls)

    return feed_urls[0][0]


def _get_feed_site_url(site_url: str | None, feed_url: str) -> str:
    if site_url is None or not is_url_valid(site_url):
        parsed_feed_url = urlparse(feed_url)
        return f"{parsed_feed_url.scheme}://{parsed_feed_url.netloc}"

    return _normalize_found_url(site_url)


def _normalize_found_url(url: str):
    if url.startswith("//"):
        url = f"https:{url}"

    return url


def _parse_articles_in_feed(
    feed_url: str, feed_title: str, parsed_feed: FeedParserDict
) -> list[ArticleData]:
    articles_data = []
    for entry in parsed_feed.entries:
        try:
            article_url = _get_article_url(feed_url, entry)
            content = _get_article_content(entry)
            articles_data.append(
                ArticleData(
                    external_article_id=entry.get("id", article_url),
                    title=entry.title,
                    summary=_get_summary(article_url, entry),
                    content=content,
                    authors=_get_article_authors(entry),
                    contributors=_get_article_contributors(entry),
                    tags=_get_articles_tags(entry),
                    url=article_url,
                    preview_picture_url=_get_preview_picture_url(article_url, entry),
                    preview_picture_alt=_get_preview_picture_alt(entry),
                    published_at=_feed_time_to_datetime(entry.get("published_parsed")),
                    updated_at=_feed_time_to_datetime(entry.get("updated_parsed")),
                    language=_get_language(parsed_feed, entry),
                    source_title=feed_title,
                )
            )
        except FailedToParseArticleError:
            logger.exception("Failed to parse an article")

    return articles_data


def _get_summary(article_url: str, entry) -> str:
    summary = ""
    if proper_summary := entry.get("summary"):
        summary = proper_summary

    if not summary and _is_youtube_url(article_url):
        summary = _get_preview_picture_alt(entry)

    return summary


def _is_youtube_url(url: str) -> bool:
    youtube_domains = {
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "youtube.googleapis.com",
        "m.youtube.com",
    }
    parsed_url = urlparse(url)

    return parsed_url.netloc in youtube_domains


def _get_article_authors(entry):
    if authors := entry.get("authors", []):
        return [author["name"] for author in authors if author.get("name")]

    if author := entry.get("author", ""):
        return [author]

    return []


def _get_article_contributors(entry):
    return [contributor["name"] for contributor in entry.get("contributors", [])]


def _get_article_content(entry):
    content_entry = _get_article_content_entry(entry)
    content_value = content_entry.get("value", "")
    if content_entry.get("type") == "application/xhtml+xml":
        content_value = unescape(content_value)

    return content_value


def _get_article_content_entry(entry):
    for content_entry in entry.get("content", []):
        if content_entry["type"] in {"text/html", "plain", "text/plain", "application/xhtml+xml"}:
            return content_entry

    return {}


def _get_language(parsed_feed, entry):
    content_entry = _get_article_content_entry(entry)
    return (
        content_entry.get("language")
        or content_entry.get("lang")
        or parsed_feed["feed"].get("language")
    )


def _get_articles_tags(entry):
    parsed_tags = set()

    if not (tags := entry.get("tags", [])):
        return []

    for term in tags:
        if not (term_value := term.get("term")):
            continue
        parsed_tags |= parse_tags_list(term_value)

    return sorted(parsed_tags)


def _get_article_url(feed_url, entry):
    try:
        return normalize_url(feed_url, entry.link)
    except ValueError as e:
        raise FailedToParseArticleError(
            f"Failed to normalize article link {entry.link} (feed {feed_url})"
        ) from e


def _get_preview_picture_url(article_url, entry) -> str:
    preview_picture_url = ""
    if (media_thumbnail := entry.get("media_thumbnail")) and (
        media_thumbnail_url := media_thumbnail[0].get("url")
    ):
        try:
            preview_picture_url = normalize_url(article_url, media_thumbnail_url)
        except ValueError:
            preview_picture_url = media_thumbnail_url

    if (
        not preview_picture_url
        and (media_content := entry.get("media_content", []))
        and (media_content_url := media_content[0].get("url"))
    ):
        try:
            # It can be a video. Normally, if it's the case we expect to have a thumbnail.
            # But we cannot be sure.
            normalized_picture_url = normalize_url(article_url, media_content_url)
            if media_content[0].get("medium") == "image" or _is_image_url(normalized_picture_url):
                preview_picture_url = normalized_picture_url
        except ValueError:
            preview_picture_url = ""

    return preview_picture_url


def _is_image_url(url: str) -> bool:
    parsed_url = urlparse(url)
    return (
        re.match(
            r".*\.(png|apng|avif|gif|jpg|jpeg|jfif|pjpeg|pjp|svg|bmp|tiff|tif|webp)$",
            parsed_url.path,
        )
        is not None
    )


def _get_preview_picture_alt(entry) -> str:
    preview_picture_alt = ""
    if (media_description := entry.get("media_description")) and (
        media_description_content := media_description[0].get("content")
    ):
        preview_picture_alt = media_description_content
    elif (media_title := entry.get("media_title")) and (
        media_title_content := media_title[0].get("content")
    ):
        preview_picture_alt = media_title_content

    if (media_credit := entry.get("media_credit")) and (
        media_credit_content := media_credit[0].get("content")
    ):
        preview_picture_alt += f" {media_credit_content}"

    return preview_picture_alt.strip()


def _feed_time_to_datetime(time_value: time.struct_time):
    if not time_value:
        return None

    return datetime.fromtimestamp(time.mktime(time_value), tz=UTC)


def _parse_feed_time(time_value: time.struct_time | None) -> datetime | None:
    if not time_value:
        return None

    return _feed_time_to_datetime(time_value)
