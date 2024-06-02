from datetime import UTC, datetime

import factory
from factory.django import DjangoModelFactory

from legadilo.users.tests.factories import UserFactory

from ..models import Article, ArticleFetchError, ReadingList, Tag


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
