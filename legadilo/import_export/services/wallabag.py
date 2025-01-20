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
    FullSanitizeValidator,
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
    title: Annotated[str, FullSanitizeValidator]
    url: Annotated[str, ValidUrlValidator]
    content: Annotated[str, sanitize_keep_safe_tags_validator()] = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_by: Annotated[tuple[CleanedString, ...], remove_falsy_items(tuple)] = ()
    reading_time: int = 0
    domain_name: Annotated[str, FullSanitizeValidator]
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
        link = wallabag_article.url

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
            link=link,
            annotations=wallabag_article.annotations,
            preview_picture_url=str(wallabag_article.preview_picture),
            preview_picture_alt="",
            published_at=wallabag_article.created_at,
            updated_at=wallabag_article.updated_at,
            language=wallabag_article.language,
        )
        Article.objects.update_or_create_from_articles_list(
            user=user,
            articles_data=[article_data],
            tags=tags,
            source_type=reading_constants.ArticleSourceType.MANUAL,
        )
        nb_added_articles += 1

    return nb_added_articles
