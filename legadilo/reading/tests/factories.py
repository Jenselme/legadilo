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

from datetime import UTC, datetime

import factory
from factory.django import DjangoModelFactory

from legadilo.users.tests.factories import UserFactory

from ..models import Article, ArticleFetchError, Comment, ReadingList, Tag


class ArticleFactory(DjangoModelFactory):
    title = factory.Sequence(lambda n: f"Article {n}")
    summary = ""
    content = ""
    authors: list[str] = []
    contributors: list[str] = []
    external_tags: list[str] = []
    link = factory.Sequence(lambda n: f"https://example.com/article/{n}")
    published_at = datetime.now(tz=UTC)
    updated_at = datetime.now(tz=UTC)
    external_article_id = factory.Sequence(lambda n: f"article-{n}")

    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Article


class ReadingListFactory(DjangoModelFactory):
    title = factory.Sequence(lambda n: f"Reading list {n}")
    slug = factory.Sequence(lambda n: f"reading-list-{n}")

    user = factory.SubFactory(UserFactory)

    class Meta:
        model = ReadingList


class TagFactory(DjangoModelFactory):
    title = factory.Sequence(lambda n: f"Tag {n}")
    slug = factory.Sequence(lambda n: f"tag-{n}")
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Tag


class ArticleFetchErrorFactory(DjangoModelFactory):
    message = "Error"
    article = factory.SubFactory(ArticleFactory)

    class Meta:
        model = ArticleFetchError


class CommentFactory(DjangoModelFactory):
    text = factory.Sequence(lambda n: f"Comment {n}")
    article = factory.SubFactory(ArticleFactory)

    class Meta:
        model = Comment
