# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.template.defaultfilters import truncatewords_html
from pydantic import BaseModel as BaseSchema
from pydantic import model_validator
from slugify import slugify

from legadilo.reading import constants
from legadilo.utils.http_utils import get_sync_client
from legadilo.utils.security import (
    full_sanitize,
    sanitize_keep_safe_tags,
)
from legadilo.utils.time_utils import safe_datetime_parse
from legadilo.utils.validators import (
    CleanedString,
    FullSanitizeValidator,
    LanguageCodeValidatorOrDefault,
    TableOfContentItem,
    TableOfContentTopItem,
    ValidUrlValidator,
    default_frozen_model_config,
    is_url_valid,
    none_to_value,
    normalize_url,
    remove_falsy_items,
    sanitize_keep_safe_tags_validator,
    truncate,
)

logger = logging.getLogger(__name__)


Language = Annotated[
    str,
    FullSanitizeValidator,
    truncate(constants.LANGUAGE_CODE_MAX_LENGTH),
    LanguageCodeValidatorOrDefault,
    none_to_value(""),
]
OptionalUrl = Literal[""] | Annotated[str, ValidUrlValidator]


class ArticleData(BaseSchema):
    model_config = default_frozen_model_config

    external_article_id: Annotated[
        str, FullSanitizeValidator, truncate(constants.EXTERNAL_ARTICLE_ID_MAX_LENGTH)
    ]
    source_title: Annotated[
        str, FullSanitizeValidator, truncate(constants.ARTICLE_SOURCE_TITLE_MAX_LENGTH)
    ]
    title: Annotated[str, FullSanitizeValidator]
    summary: Annotated[
        str,
        sanitize_keep_safe_tags_validator(constants.EXTRA_TAGS_TO_REMOVE_FROM_SUMMARY),
    ]
    content: Annotated[str, sanitize_keep_safe_tags_validator()]
    table_of_content: tuple[TableOfContentTopItem, ...] = ()
    authors: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()
    contributors: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()
    tags: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()
    url: Annotated[str, ValidUrlValidator]
    preview_picture_url: OptionalUrl = ""
    preview_picture_alt: Annotated[str, FullSanitizeValidator, none_to_value("")] = ""
    published_at: datetime | None = None
    updated_at: datetime | None = None
    language: Language
    annotations: tuple[str, ...] = ()
    read_at: datetime | None = None
    is_favorite: bool = False

    @model_validator(mode="before")
    @staticmethod
    def prepare_values(
        values: dict[str, Any],
    ) -> dict[str, Any]:
        summary = values.get("summary", "")
        content = values.get("content", "")
        title = values.get("title", "")
        source_title = values.get("source_title", "")
        url = values.get("url")

        # Consider link optional here to please mypy. It's mandatory anyway so validation will fail
        # later if needed.
        if url:
            summary = _resolve_relative_urls(url, summary)
            content = _resolve_relative_urls(url, content)

        content, table_of_content = _build_table_of_content(content)

        if not summary and content:
            summary = _get_fallback_summary_from_content(content)

        if not title:
            title = urlparse(values.get("url")).netloc

        if not source_title:
            source_title = urlparse(values.get("url")).netloc

        return {
            **values,
            "summary": summary,
            "content": content,
            "title": title,
            "source_title": source_title,
            "table_of_content": table_of_content,
        }


def _resolve_relative_urls(article_url: str, content: str) -> str:
    soup = BeautifulSoup(content, "html.parser")
    for link in soup.find_all("a"):
        if (href := link.get("href")) is None:
            continue

        link["href"] = _normalize_url(article_url, href)

    for image in soup.find_all("img"):
        if (src := image.get("src")) is None:
            continue

        image["src"] = _normalize_url(article_url, src)

    return str(soup)


def _normalize_url(article_url: str, elt_url: str):
    try:
        return normalize_url(article_url, elt_url)
    except ValueError:
        logger.info(f"Failed to normalize url {elt_url=} against {article_url=}")
        return elt_url


class ArticleTooBigError(Exception):
    pass


def get_article_from_url(url: str) -> ArticleData:
    url, soup, content_language = _get_page_content(url)

    return _build_article_data_from_soup(
        url,
        soup,
        content_language=content_language,
    )


def build_article_data_from_content(*, url: str, title: str, content: str) -> ArticleData:
    soup = BeautifulSoup(content, "html.parser")

    return _build_article_data_from_soup(url, soup, forced_title=title)


def _get_page_content(url: str) -> tuple[str, BeautifulSoup, str | None]:
    with get_sync_client() as client:
        # We can have HTTP redirect with the meta htt-equiv tag. Let's read them to up to 10 time
        # to find the final URL of the article we are looking for.
        for _ in range(10):
            response = client.get(url)
            response.raise_for_status()
            if sys.getsizeof(response.content) > constants.MAX_ARTICLE_FILE_SIZE:
                raise ArticleTooBigError
            soup = BeautifulSoup(
                response.content.decode(response.encoding or "utf-8"), "html.parser"
            )
            if (
                (http_equiv_refresh := soup.find("meta", attrs={"http-equiv": "refresh"}))
                and (http_equiv_refresh_value := http_equiv_refresh.get("content"))  # type: ignore[union-attr]
                and (http_equiv_refresh_url := _parse_http_equiv_refresh(http_equiv_refresh_value))  # type: ignore[arg-type]
            ):
                url = http_equiv_refresh_url
                continue

            break

    return str(response.url), soup, response.headers.get("Content-Language")


def _parse_http_equiv_refresh(value: str) -> str | None:
    raw_data = value.split(";")
    if len(raw_data) != 2:  # noqa: PLR2004 Magic value used in comparison
        return None

    url = raw_data[1]
    if url.startswith("url="):
        url = url.replace("url=", "")

    if is_url_valid(url):
        return url

    return None


def _build_article_data_from_soup(
    fetched_url: str,
    soup: BeautifulSoup,
    *,
    content_language: str | None = None,
    forced_title: str | None = None,
) -> ArticleData:
    content = _get_content(soup)

    return ArticleData(
        external_article_id="",
        source_title=_get_site_title(fetched_url, soup),
        title=forced_title or _get_title(soup),
        summary=_get_summary(soup),
        content=content,
        authors=tuple(_get_authors(soup)),
        contributors=(),
        tags=tuple(_get_tags(soup)),
        url=_get_url(fetched_url, soup),
        preview_picture_url=_get_preview_picture_url(fetched_url, soup),
        preview_picture_alt="",
        published_at=_get_published_at(soup),
        updated_at=_get_updated_at(soup),
        language=_get_lang(soup, content_language),
    )


def _get_title(soup) -> str:
    title = ""
    if (og_title := soup.find("meta", attrs={"property": "og:title"})) and og_title.get("content"):
        title = og_title.get("content")
    elif (itemprop_name := soup.find("meta", attrs={"itemprop": "name"})) and itemprop_name.get(
        "content"
    ):
        title = itemprop_name.get("content")
    elif (meta_title := soup.find("meta", attrs={"property": "title"})) and meta_title.get(
        "content"
    ):
        title = meta_title.get("content")
    elif (title_tag := soup.find("title")) and title_tag.text:
        title = title_tag.text
    elif (h1_tag := soup.find("h1")) and h1_tag.text:
        title = h1_tag.text

    return title


def _get_site_title(fetched_url: str, soup) -> str:
    site_title = urlparse(fetched_url).netloc
    if (og_site_name := soup.find("meta", attrs={"property": "og:site_name"})) and og_site_name.get(
        "content"
    ):
        site_title = og_site_name.get("content")
    elif (title_tag := soup.find("title")) and title_tag.text:
        site_title = title_tag.text

    return site_title


def _get_summary(soup) -> str:
    summary = ""
    if (
        og_description := soup.find("meta", attrs={"property": "og:description"})
    ) and og_description.get("content"):
        summary = og_description.get("content")
    elif (meta_desc := soup.find("meta", attrs={"name": "description"})) and meta_desc.get(
        "content"
    ):
        summary = meta_desc.get("content")
    elif (
        itemprop_description := soup.find("meta", attrs={"itemprop": "description"})
    ) and itemprop_description.get("content"):
        summary = itemprop_description.get("content")

    return summary


def _get_fallback_summary_from_content(content: str) -> str:
    return truncatewords_html(
        sanitize_keep_safe_tags(
            content,
            extra_tags_to_cleanup=constants.EXTRA_TAGS_TO_REMOVE_FROM_SUMMARY,
        ),
        constants.MAX_SUMMARY_LENGTH,
    )


def _get_content(soup) -> str:
    articles = soup.find_all("article")
    article_content = None
    if len(articles) > 1:
        article_content = _parse_multiple_articles(soup)
    elif len(articles) > 0:
        article_content = articles[0]

    if article_content is None:
        article_content = soup.find("main")
    if article_content is None:
        article_content = soup.find("body")

    if not article_content:
        return ""

    tags_to_cleanup = {"noscript", "footer", "header", "nav", "aside"}
    # Some invalid articles may have multiple h1, keep them in this case since they are "normal"
    # article titles and thus must be kept.
    if len(soup.find_all("h1")) == 1:
        tags_to_cleanup.add("h1")

    for tag_name in tags_to_cleanup:
        _extract_tag_from_content(article_content, tag_name)
    return str(article_content)


def _parse_multiple_articles(soup):
    for article in soup.find_all(["article", "section"]):
        attrs = set()
        if article_id := article.get("id"):
            attrs.update(article_id)
        if article_class := article.get("class"):
            attrs.update(article_class)

        if (
            len(
                attrs.intersection({
                    "post__content",
                    "article__content",
                    "post-content",
                    "article-content",
                    "article",
                    "post",
                    "content",
                })
            )
            > 0
        ):
            return article

    return soup.find("article")


def _extract_tag_from_content(soup, tag_name: str):
    for tag in soup.find_all(tag_name):
        tag.extract()


def _get_authors(soup) -> list[str]:
    authors = []
    if (meta_author := soup.find("meta", {"name": "author"})) and meta_author.get("content"):
        authors = [meta_author.get("content")]

    return authors


def _get_tags(soup) -> list[str]:
    tags = set()

    if article_tags := soup.find_all("meta", attrs={"property": "article:tag"}):
        for meta_tag in article_tags:
            tags |= parse_tags_list(meta_tag.get("content"))
    elif (keywords := soup.find("meta", attrs={"property": "keywords"})) and keywords.get(
        "content"
    ):
        tags = parse_tags_list(keywords.get("content"))

    return sorted(tags)


def parse_tags_list(tags_str: str) -> set[str]:
    parsed_tags = set()
    for raw_tag in tags_str.split(","):
        tag = full_sanitize(raw_tag).strip()
        if not tag:
            continue
        parsed_tags.add(tag)

    return parsed_tags


def _get_url(fetched_url: str, soup) -> str:
    url = fetched_url
    if (canonical_url := soup.find("link", {"rel": "canonical"})) and canonical_url.get("href"):
        url = canonical_url.get("href")

    if is_url_valid(url):
        return normalize_url(fetched_url, url)

    return fetched_url


def _get_preview_picture_url(fetched_url, soup) -> str:
    preview_picture_url = ""

    if (og_image := soup.find("meta", attrs={"property": "og:image"})) and (
        og_image_url := og_image.get("content")
    ):
        try:
            preview_picture_url = normalize_url(fetched_url, og_image_url)
        except ValueError:
            preview_picture_url = ""
    if (
        not preview_picture_url
        and (itemprop_image := soup.find("meta", attrs={"itemprop": "image"}))
        and (itemprop_url := itemprop_image.get("content"))
    ):
        try:
            preview_picture_url = normalize_url(fetched_url, itemprop_url)
        except ValueError:
            preview_picture_url = ""
    if (
        not preview_picture_url
        and (twitter_image := soup.find("meta", attrs={"property": "twitter:image"}))
        and (twitter_image_url := twitter_image.get("content"))
        and is_url_valid(twitter_image_url)
    ):
        try:
            preview_picture_url = normalize_url(fetched_url, twitter_image_url)
        except ValueError:
            preview_picture_url = ""

    return preview_picture_url


def _get_published_at(soup) -> datetime | None:
    published_at = None
    if (
        article_published_time := soup.find("meta", attrs={"property": "article:published_time"})
    ) and article_published_time.get("content"):
        published_at = safe_datetime_parse(article_published_time.get("content"))

    return published_at


def _get_updated_at(soup) -> datetime | None:
    updated_at = None
    if (
        article_modified_time := soup.find("meta", attrs={"property": "article:modified_time"})
    ) and article_modified_time.get("content"):
        updated_at = safe_datetime_parse(article_modified_time.get("content"))

    return updated_at


def _get_lang(soup, content_language: str | None) -> str:
    if not soup.find("html") or (language := soup.find("html").get("lang")) is None:
        language = content_language

    return str(language or "")


def _build_table_of_content(content: str) -> tuple[str, list[TableOfContentTopItem]]:
    soup = BeautifulSoup(content, "html.parser")
    toc = []
    toc_item_top_level: TableOfContentTopItem | None = None

    for header in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = full_sanitize(header.text)
        id_ = header.get("id") or slugify(text)
        header["id"] = id_
        level = int(header.name.replace("h", ""))
        # If the content is well-structured, all top level title will be at the same level.
        # Since we don't know, we allow for a first h2 to be followed by a h1.
        if toc_item_top_level is None or level <= toc_item_top_level.level:
            toc_item_top_level = TableOfContentTopItem(id=id_, text=text, level=level)
            toc.append(toc_item_top_level)
        # We only allow one level in the TOC. It's enough.
        elif level == toc_item_top_level.level + 1:
            toc_item_top_level.children.append(TableOfContentItem(id=id_, text=text, level=level))

    return str(soup), toc
