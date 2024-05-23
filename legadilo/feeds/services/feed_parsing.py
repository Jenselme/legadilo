import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import chain
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from feedparser import FeedParserDict
from feedparser import parse as parse_feed

from legadilo.reading import constants as reading_constants
from legadilo.reading.utils.article_fetching import ArticleData
from legadilo.utils.security import full_sanitize, sanitize_keep_safe_tags

from ...utils.time import dt_to_http_date
from ...utils.validators import language_code_validator, normalize_url
from .. import constants


@dataclass(frozen=True)
class FeedData:
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


async def get_feed_data(
    url: str,
    *,
    client: httpx.AsyncClient,
    etag: str | None = None,
    last_modified: datetime | None = None,
) -> FeedData:
    """Find the feed data from the supplied URL.

    It's either a feed or a page containing a link to a feed.
    """
    parsed_feed, url_content, resolved_url = await _fetch_feed_and_raw_data(client, url)
    if not parsed_feed.get("version"):
        url = _find_feed_page_content(url_content)
        parsed_feed, resolved_url = await _fetch_feed(
            client, url, etag=etag, last_modified=last_modified
        )

    return build_feed_data(parsed_feed, str(resolved_url))


def build_feed_data(parsed_feed: FeedParserDict, resolved_url: str) -> FeedData:
    feed_title = full_sanitize(parsed_feed.feed.get("title", ""))
    return FeedData(
        feed_url=resolved_url,
        site_url=_normalize_found_link(parsed_feed.feed.get("link", resolved_url)),
        title=feed_title,
        description=full_sanitize(parsed_feed.feed.get("description", "")),
        feed_type=constants.SupportedFeedType(parsed_feed.version),
        articles=_parse_articles_in_feed(resolved_url, feed_title, parsed_feed),
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

    response = await client.get(url, headers=headers, follow_redirects=True)
    raw_feed_content = response.raise_for_status().content
    if sys.getsizeof(raw_feed_content) > constants.MAX_FEED_FILE_SIZE:
        raise FeedFileTooBigError

    feed_content = raw_feed_content.decode(response.encoding or "utf-8")
    return (
        parse_feed(feed_content, resolve_relative_uris=True, sanitize_html=False),
        feed_content,
        response.url,
    )


async def _fetch_feed(
    client: httpx.AsyncClient, url: str, *, etag: str | None, last_modified: datetime | None
) -> tuple[FeedParserDict, httpx.URL]:
    parsed_feed, _, resolved_url = await _fetch_feed_and_raw_data(
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


def _parse_articles_in_feed(
    feed_url: str, feed_title: str, parsed_feed: FeedParserDict
) -> list[ArticleData]:
    articles_data = []
    for entry in parsed_feed.entries:
        article_link = _get_article_link(feed_url, entry)
        articles_data.append(
            ArticleData(
                external_article_id=full_sanitize(entry.get("id", "")),
                title=full_sanitize(entry.title),
                summary=_get_summary(article_link, entry),
                content=_get_article_content(entry),
                authors=_get_article_authors(entry),
                contributors=_get_article_contributors(entry),
                tags=_get_articles_tags(entry),
                link=article_link,
                preview_picture_url=_get_preview_picture_url(article_link, entry),
                preview_picture_alt=_get_preview_picture_alt(entry),
                published_at=_feed_time_to_datetime(entry.get("published_parsed")),
                updated_at=_feed_time_to_datetime(entry.get("updated_parsed")),
                language=_get_language(parsed_feed, entry),
                source_title=feed_title,
            )
        )

    return articles_data


def _get_summary(article_url: str, entry) -> str:
    summary = ""
    if proper_summary := entry.get("summary"):
        summary = proper_summary

    if not summary and _is_youtube_link(article_url):
        summary = _get_preview_picture_alt(entry)

    return sanitize_keep_safe_tags(
        summary, extra_tags_to_cleanup=reading_constants.EXTRA_TAGS_TO_REMOVE_FROM_SUMMARY
    )


def _is_youtube_link(link: str) -> bool:
    youtube_domains = {
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "youtube.googleapis.com",
        "m.youtube.com",
    }
    parsed_link = urlparse(link)

    return parsed_link.netloc in youtube_domains


def _get_article_authors(entry):
    if authors := entry.get("authors", []):
        return [full_sanitize(author["name"]) for author in authors if author.get("name")]

    if author := entry.get("author", ""):
        return [full_sanitize(author)]

    return []


def _get_article_contributors(entry):
    return [full_sanitize(contributor["name"]) for contributor in entry.get("contributors", [])]


def _get_article_content(entry):
    content_entry = _get_article_content_entry(entry)
    return sanitize_keep_safe_tags(content_entry.get("value", ""))


def _get_article_content_entry(entry):
    for content_entry in entry.get("content", []):
        if content_entry["type"] in {"text/html", "plain", "text/plain", "application/xhtml+xml"}:
            return content_entry

    return {}


def _get_language(parsed_feed, entry):
    content_entry = _get_article_content_entry(entry)
    try:
        language = (
            content_entry.get("language")
            or content_entry.get("lang")
            or parsed_feed["feed"].get("language")
        )
        language_code_validator(language)
    except ValidationError:
        language = ""

    return language


def _get_articles_tags(entry):
    parsed_tags = set()

    if not (tags := entry.get("tags", [])):
        return []

    for term in tags:
        if not (term_value := term.get("term")):
            continue
        for raw_tag in term_value.split(","):
            tag = full_sanitize(raw_tag).strip()
            if not tag:
                continue
            parsed_tags.add(tag)

    return sorted(parsed_tags)


def _get_article_link(feed_url, entry):
    try:
        return normalize_url(feed_url, entry.link)
    except ValueError as e:
        raise InvalidFeedArticleError from e


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
            if media_content[0].get("medium") == "image" or _is_image_link(normalized_picture_url):
                preview_picture_url = normalized_picture_url
        except ValueError:
            preview_picture_url = ""

    return preview_picture_url


def _is_image_link(link: str) -> bool:
    parsed_link = urlparse(link)
    return (
        re.match(
            r".*\.(png|apng|avif|gif|jpg|jpeg|jfif|pjpeg|pjp|svg|bmp|tiff|tif|webp)$",
            parsed_link.path,
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

    return full_sanitize(preview_picture_alt.strip())


def _feed_time_to_datetime(time_value: time.struct_time):
    if not time_value:
        return None

    return datetime.fromtimestamp(time.mktime(time_value), tz=UTC)


def _parse_feed_time(time_value: time.struct_time | None) -> datetime | None:
    if not time_value:
        return None

    return _feed_time_to_datetime(time_value)
