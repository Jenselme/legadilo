import json
import logging
from pathlib import Path
from typing import Any

from django.template.defaultfilters import truncatewords_html
from jsonschema import validate as validate_json_schema
from slugify import slugify

from legadilo.import_export.services.exceptions import InvalidEntryError
from legadilo.reading import constants as reading_constants
from legadilo.reading.models import Article, ArticleTag, Tag
from legadilo.users.models import User
from legadilo.utils.security import full_sanitize, sanitize_keep_safe_tags
from legadilo.utils.time import safe_datetime_parse, utcnow
from legadilo.utils.validators import is_url_valid

logger = logging.getLogger(__name__)


def import_wallabag_json_file(user: User, path_to_file: str) -> int:
    with Path(path_to_file).open("rb") as f:
        data = json.load(f)

    return _import_wallabag_data(user, data)


def _import_wallabag_data(user: User, data: list[dict]) -> int:
    _validate_data_batch(data)
    nb_added_articles = 0
    for article_data in data:
        title = full_sanitize(article_data["title"])[: reading_constants.ARTICLE_TITLE_MAX_LENGTH]
        content = sanitize_keep_safe_tags(article_data.get("content", ""))
        preview_picture_url = article_data.get("preview_picture", "")
        link = article_data["url"]
        if preview_picture_url and not is_url_valid(preview_picture_url):
            logger.debug(f"Some preview url link {preview_picture_url} is not valid")
            preview_picture_url = ""
        if not is_url_valid(link):
            raise InvalidEntryError(f"The article URL ({link}) is not valid")

        article, created = Article.objects.get_or_create(
            user=user,
            link=link,
            defaults={
                "title": title,
                "slug": slugify(title),
                "summary": truncatewords_html(content, 255),
                "content": content,
                "reading_time": int(article_data["reading_time"]),
                "authors": [
                    full_sanitize(author) for author in article_data.get("published_by", [])
                ],
                "published_at": safe_datetime_parse(article_data["created_at"]),
                "updated_at": safe_datetime_parse(article_data["updated_at"]),
                "initial_source_type": reading_constants.ArticleSourceType.MANUAL,
                "initial_source_title": full_sanitize(article_data["domain_name"][:100]),
                "preview_picture_url": preview_picture_url,
                "external_article_id": f"wallabag:{article_data["id"]}",
                "read_at": utcnow() if article_data["is_archived"] else None,
                "is_favorite": bool(article_data["is_starred"]),
            },
        )
        if created:
            nb_added_articles += 1
        else:
            logger.debug(
                f"Article with link {article.link} already exists "
                f"({article.id}, {article.external_article_id})"
            )

        tags = Tag.objects.get_or_create_from_list(user, article_data.get("tags", []))
        ArticleTag.objects.associate_articles_with_tags(
            [article], tags, tagging_reason=reading_constants.TaggingReason.ADDED_MANUALLY
        )

    return nb_added_articles


def _validate_data_batch(article_data: Any):
    validate_json_schema(
        article_data,
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "number"},
                    "is_archived": {"type": "number"},
                    "is_starred": {"type": "number"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "content": {"type": "string"},
                    "created_at": {"type": "string"},
                    "updated_at": {"type": "string"},
                    "published_by": {"type": "array", "items": {"type": "string"}},
                    "reading_time": {"type": "number"},
                    "domain_name": {"type": "string"},
                    "preview_picture": {"type": "string"},
                },
                "required": [
                    "id",
                    "is_archived",
                    "is_starred",
                    "title",
                    "url",
                    "created_at",
                    "updated_at",
                    "reading_time",
                    "domain_name",
                ],
            },
        },
    )
