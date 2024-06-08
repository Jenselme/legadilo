import json
import logging
from pathlib import Path
from typing import Any

from jsonschema import validate as validate_json_schema

from legadilo.import_export.services.exceptions import InvalidEntryError
from legadilo.reading import constants as reading_constants
from legadilo.reading.models import Article, Tag
from legadilo.reading.services.article_fetching import build_article_data
from legadilo.users.models import User
from legadilo.utils.time import safe_datetime_parse
from legadilo.utils.validators import is_url_valid

logger = logging.getLogger(__name__)


def import_wallabag_json_file(user: User, path_to_file: str) -> int:
    with Path(path_to_file).open("rb") as f:
        data = json.load(f)

    return _import_wallabag_data(user, data)


def _import_wallabag_data(user: User, data: list[dict]) -> int:
    _validate_data_batch(data)
    nb_added_articles = 0
    for raw_article_data in data:
        link = raw_article_data["url"]
        preview_picture_url = raw_article_data.get("preview_picture", "")
        if preview_picture_url and not is_url_valid(preview_picture_url):
            logger.debug(f"Some preview url link {preview_picture_url} is not valid")
            preview_picture_url = ""
        if not is_url_valid(link):
            raise InvalidEntryError(f"The article URL ({link}) is not valid")

        tags = Tag.objects.get_or_create_from_list(user, raw_article_data.get("tags", []))
        article_data = build_article_data(
            external_article_id=f"wallabag:{raw_article_data["id"]}",
            source_title=raw_article_data["domain_name"],
            title=raw_article_data["title"],
            summary="",
            content=raw_article_data.get("content", ""),
            authors=raw_article_data.get("published_by", []),
            contributors=[],
            tags=[],
            link=link,
            annotations=raw_article_data.get("annotations", []),
            preview_picture_url=preview_picture_url,
            preview_picture_alt="",
            published_at=safe_datetime_parse(raw_article_data["created_at"]),
            updated_at=safe_datetime_parse(raw_article_data["updated_at"]),
            language=raw_article_data.get("language", ""),
        )
        Article.objects.update_or_create_from_articles_list(
            user=user,
            articles_data=[article_data],
            tags=tags,
            source_type=reading_constants.ArticleSourceType.MANUAL,
        )
        nb_added_articles += 1

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
                    "annotations": {"type": "array"},
                    "language": {"type": "string"},
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
