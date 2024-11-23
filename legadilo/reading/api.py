# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
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
from operator import xor
from typing import Annotated, Self

from asgiref.sync import async_to_sync
from ninja import ModelSchema, Router, Schema
from ninja.pagination import paginate
from pydantic import Field, model_validator

from legadilo.reading import constants
from legadilo.reading.models import Article, Tag
from legadilo.reading.services.article_fetching import (
    build_article_data_from_content,
    get_article_from_url,
)
from legadilo.users.user_types import AuthenticatedHttpRequest
from legadilo.utils.validators import ValidUrlValidator

reading_api_router = Router(tags=["reading"])


class OutArticleSchema(ModelSchema):
    class Meta:
        model = Article
        exclude = ("user", "obj_created_at", "obj_updated_at")


class InArticleSchema(Schema):
    link: Annotated[str, ValidUrlValidator]
    title: str = ""
    content: str = ""
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_title_and_content(self) -> Self:
        if xor(len(self.title) > 0, len(self.content) > 0):
            raise ValueError("You must supply either both title and content or none of them")

        return self

    @property
    def has_data(self) -> bool:
        return bool(self.title) and bool(self.content)


@reading_api_router.get("/articles/", response=list[OutArticleSchema])
@paginate
def list_articles(request: AuthenticatedHttpRequest):
    return Article.objects.get_queryset().for_user(request.user).default_order_by()


@reading_api_router.post("/articles/", response=OutArticleSchema)
def create_article(request: AuthenticatedHttpRequest, article: InArticleSchema):
    if article.has_data:
        article_data = build_article_data_from_content(
            url=article.link, title=article.title, content=article.content
        )
    else:
        article_data = async_to_sync(get_article_from_url)(article.link)

    # Tags specified in article data are the raw tags used in feeds, they are not used to link an
    # article to tag objects.
    tags = Tag.objects.get_or_create_from_list(request.user, article.tags)
    article_data = article_data.model_copy(update={"tags": ()})

    articles = Article.objects.update_or_create_from_articles_list(
        request.user, [article_data], tags, source_type=constants.ArticleSourceType.MANUAL
    )
    return articles[0]
