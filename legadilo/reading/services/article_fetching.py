import sys
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.template.defaultfilters import truncatewords_html

from legadilo.reading import constants
from legadilo.utils.http import get_async_client
from legadilo.utils.security import (
    full_sanitize,
    sanitize_keep_safe_tags,
)
from legadilo.utils.time import safe_datetime_parse
from legadilo.utils.validators import is_url_valid, language_code_validator, normalize_url


@dataclass(frozen=True)
class ArticleData:
    external_article_id: str
    source_title: str
    title: str
    summary: str
    content: str
    authors: list[str]
    contributors: list[str]
    tags: list[str]
    link: str
    preview_picture_url: str
    preview_picture_alt: str
    published_at: datetime | None
    updated_at: datetime | None
    language: str
    annotations: list[str] | tuple[str] = field(default_factory=list)
    read_at: datetime | None = None
    is_favorite: bool = False


def build_article_data(  # noqa: PLR0913 too many arguments
    *,
    external_article_id: str,
    source_title: str,
    title: str,
    summary: str,
    content: str,
    authors: list[str],
    contributors: list[str],
    tags: list[str],
    link: str,
    preview_picture_url: str,
    preview_picture_alt: str,
    published_at: datetime | None,
    updated_at: datetime | None,
    language: str,
    annotations: list[str] | tuple[str] = (),  # type: ignore[assignment]
    read_at: datetime | None = None,
    is_favorite: bool = False,
) -> ArticleData:
    if not summary and content:
        summary = _get_fallback_summary_from_content(content)

    try:
        language = full_sanitize(language)
        language_code_validator(language)
    except (ValidationError, TypeError):
        language = ""

    return ArticleData(
        external_article_id=full_sanitize(external_article_id)[
            : constants.EXTERNAL_ARTICLE_ID_MAX_LENGTH
        ],
        source_title=full_sanitize(source_title)[: constants.ARTICLE_SOURCE_TITLE_MAX_LENGTH],
        title=full_sanitize(title)[: constants.ARTICLE_TITLE_MAX_LENGTH],
        summary=sanitize_keep_safe_tags(
            summary, extra_tags_to_cleanup=constants.EXTRA_TAGS_TO_REMOVE_FROM_SUMMARY
        ),
        content=sanitize_keep_safe_tags(content),
        authors=_sanitize_lists(authors),
        contributors=_sanitize_lists(contributors),
        tags=_sanitize_lists(tags),
        link=link,
        preview_picture_url=preview_picture_url,
        preview_picture_alt=full_sanitize(preview_picture_alt),
        published_at=published_at,
        updated_at=updated_at,
        language=full_sanitize(language)[: constants.LANGUAGE_CODE_MAX_LENGTH],
        annotations=annotations,
        read_at=read_at,
        is_favorite=is_favorite,
    )


def _sanitize_lists(alist: list[str]) -> list[str]:
    cleaned_list = []
    for item in alist:
        cleaned_item = full_sanitize(item.strip())
        if cleaned_item:
            cleaned_list.append(cleaned_item)

    return cleaned_list


class ArticleTooBigError(Exception):
    pass


async def get_article_from_url(url: str) -> ArticleData:
    url, soup, content_language = await _get_page_content(url)

    return _build_article_data_from_soup(
        url,
        soup,
        content_language,
    )


async def _get_page_content(url: str) -> tuple[str, BeautifulSoup, str | None]:
    async with get_async_client() as client:
        # We can have HTTP redirect with the meta htt-equiv tag. Let's read them to up to 10 time
        # to find the final URL of the article we are looking for.
        for _ in range(10):
            response = await client.get(url)
            response.raise_for_status()
            if sys.getsizeof(response.content) > constants.MAX_ARTICLE_FILE_SIZE:
                raise ArticleTooBigError
            soup = BeautifulSoup(
                response.content.decode(response.encoding or "utf-8"), "html.parser"
            )
            if (
                (http_equiv_refresh := soup.find("meta", attrs={"http-equiv": "refresh"}))
                and (http_equiv_refresh_value := http_equiv_refresh.get("content"))
                and (http_equiv_refresh_url := _parse_http_equiv_refresh(http_equiv_refresh_value))
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
    fetched_url: str, soup: BeautifulSoup, content_language: str | None
) -> ArticleData:
    content = _get_content(soup)

    return build_article_data(
        external_article_id="",
        source_title=_get_site_title(fetched_url, soup),
        title=_get_title(soup),
        summary=_get_summary(soup, content),
        content=content,
        authors=_get_authors(soup),
        contributors=[],
        tags=_get_tags(soup),
        link=_get_link(fetched_url, soup),
        preview_picture_url=_get_preview_picture_url(fetched_url, soup),
        preview_picture_alt="",
        published_at=_get_published_at(soup),
        updated_at=_get_updated_at(soup),
        language=_get_lang(soup, content_language),
    )


def _get_title(soup: BeautifulSoup) -> str:
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


def _get_site_title(fetched_url: str, soup: BeautifulSoup) -> str:
    site_title = urlparse(fetched_url).netloc
    if (og_site_name := soup.find("meta", attrs={"property": "og:site_name"})) and og_site_name.get(
        "content"
    ):
        site_title = og_site_name.get("content")
    elif (title_tag := soup.find("title")) and title_tag.text:
        site_title = title_tag.text

    return site_title


def _get_summary(soup: BeautifulSoup, content: str) -> str:
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


def _get_content(soup: BeautifulSoup) -> str:
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

    for tag_name in ["noscript", "h1", "footer", "header", "nav", "aside"]:
        _extract_tag_from_content(article_content, tag_name)
    return str(article_content)


def _parse_multiple_articles(soup: BeautifulSoup):
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


def _extract_tag_from_content(soup: BeautifulSoup, tag_name: str):
    for tag in soup.find_all(tag_name):
        tag.extract()


def _get_authors(soup: BeautifulSoup) -> list[str]:
    authors = []
    if (meta_author := soup.find("meta", {"name": "author"})) and meta_author.get("content"):
        authors = [meta_author.get("content")]

    return authors


def _get_tags(soup: BeautifulSoup) -> list[str]:
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


def _get_link(fetched_url: str, soup: BeautifulSoup) -> str:
    link = fetched_url
    if (canonical_link := soup.find("link", {"rel": "canonical"})) and canonical_link.get("href"):
        link = canonical_link.get("href")

    if is_url_valid(link):
        return normalize_url(fetched_url, link)

    return fetched_url


def _get_preview_picture_url(fetched_url, soup: BeautifulSoup) -> str:
    preview_picture_url = ""

    if (og_image := soup.find("meta", attrs={"property": "og:image"})) and (
        og_image_link := og_image.get("content")
    ):
        try:
            preview_picture_url = normalize_url(fetched_url, og_image_link)
        except ValueError:
            preview_picture_url = ""
    if (
        not preview_picture_url
        and (itemprop_image := soup.find("meta", attrs={"itemprop": "image"}))
        and (itemprop_link := itemprop_image.get("content"))
    ):
        try:
            preview_picture_url = normalize_url(fetched_url, itemprop_link)
        except ValueError:
            preview_picture_url = ""
    if (
        not preview_picture_url
        and (twitter_image := soup.find("meta", attrs={"property": "twitter:image"}))
        and (twitter_image_link := twitter_image.get("content"))
        and is_url_valid(twitter_image_link)
    ):
        try:
            preview_picture_url = normalize_url(fetched_url, twitter_image_link)
        except ValueError:
            preview_picture_url = ""

    return preview_picture_url


def _get_published_at(soup: BeautifulSoup) -> datetime | None:
    published_at = None
    if (
        article_published_time := soup.find("meta", attrs={"property": "article:published_time"})
    ) and article_published_time.get("content"):
        published_at = safe_datetime_parse(article_published_time.get("content"))

    return published_at


def _get_updated_at(soup: BeautifulSoup) -> datetime | None:
    updated_at = None
    if (
        article_modified_time := soup.find("meta", attrs={"property": "article:modified_time"})
    ) and article_modified_time.get("content"):
        updated_at = safe_datetime_parse(article_modified_time.get("content"))

    return updated_at


def _get_lang(soup: BeautifulSoup, content_language: str | None) -> str:
    if not soup.find("html") or (language := soup.find("html").get("lang")) is None:
        language = content_language

    return language
