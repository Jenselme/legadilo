# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated

from django.core.files import File
from pydantic import BaseModel as BaseSchema
from pydantic import ConfigDict, TypeAdapter

from legadilo.reading import constants as reading_constants
from legadilo.reading.models import Article, Tag
from legadilo.reading.services.article_fetching import ArticleData, Language, OptionalUrl
from legadilo.users.models import User
from legadilo.utils.validators import (
    CleanedString,
    ValidUrlValidator,
    remove_falsy_items,
    sanitize_keep_safe_tags_validator,
)

logger = logging.getLogger(__name__)


class WallabagArticle(BaseSchema):
    model_config = ConfigDict(
        extra="ignore", frozen=True, validate_default=True, validate_assignment=True
    )

    id: int
    is_archived: bool
    is_starred: bool
    tags: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()
    title: CleanedString
    url: Annotated[str, ValidUrlValidator]
    content: Annotated[str, sanitize_keep_safe_tags_validator()] = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_by: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()
    reading_time: int = 0
    domain_name: CleanedString
    preview_picture: OptionalUrl = ""
    annotations: tuple[str, ...] = ()
    language: Language = ""


ListOfWallabagArticles = TypeAdapter(list[WallabagArticle])


def import_wallabag_json_file_path(user: User, path_to_file: str) -> int:
    with Path(path_to_file).open("rb") as f:
        data = json.load(f)

    return _import_wallabag_data(user, data)


def import_wallabag_file(user: User, file: File) -> int:
    return _import_wallabag_data(user, json.load(file))


def _import_wallabag_data(user: User, data: list[dict]) -> int:
    wallabag_articles = ListOfWallabagArticles.validate_python(data)
    nb_added_articles = 0
    for wallabag_article in wallabag_articles:
        url = wallabag_article.url

        tags = Tag.objects.get_or_create_from_list(user, wallabag_article.tags)
        article_data = ArticleData(
            external_article_id=f"wallabag:{wallabag_article.id}",
            source_title=wallabag_article.domain_name,
            title=wallabag_article.title,
            summary="",
            content=wallabag_article.content,
            authors=wallabag_article.published_by,
            contributors=(),
            tags=(),
            url=url,
            annotations=wallabag_article.annotations,
            preview_picture_url=str(wallabag_article.preview_picture),
            preview_picture_alt="",
            published_at=wallabag_article.created_at,
            updated_at=wallabag_article.updated_at,
            language=wallabag_article.language,
        )
        Article.objects.save_from_list_of_data(
            user=user,
            articles_data=[article_data],
            tags=tags,
            source_type=reading_constants.ArticleSourceType.MANUAL,
        )
        nb_added_articles += 1

    return nb_added_articles
