# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import UTC, datetime

import factory
from factory.django import DjangoModelFactory

from legadilo.users.tests.factories import UserFactory

from ..models import Article, ArticleFetchError, Comment, ReadingList, Tag
from ..services.article_fetching import ArticleData


class ArticleFactory(DjangoModelFactory):
    title = factory.Sequence(lambda n: f"Article {n}")
    summary = ""
    content = ""
    authors: list[str] = []
    contributors: list[str] = []
    external_tags: list[str] = []
    url = factory.Sequence(lambda n: f"https://example.com/article/{n}")
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


class ArticleDataFactory(factory.DictFactory):
    external_article_id = factory.Sequence(lambda n: f"external-id-{n}")
    source_title = factory.Sequence(lambda n: f"Source {n}")
    title = factory.Sequence(lambda n: f"Article {n}")
    summary = ""
    content = ""
    content_type = "text/plain"
    url = factory.Sequence(lambda n: f"https://example.com/article-{n}.html")
    language = "en"

    class Meta:
        model = ArticleData
