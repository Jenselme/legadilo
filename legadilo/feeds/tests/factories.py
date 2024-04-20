from datetime import UTC, datetime

import factory
from factory.django import DjangoModelFactory

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.models import FeedUpdate, ReadingList, Tag
from legadilo.users.tests.factories import UserFactory

from ..models import Article, Feed


class FeedFactory(DjangoModelFactory):
    feed_url = factory.Sequence(lambda n: f"https://example.com/feeds/{n}.xml")
    site_url = "https://example.com"
    title = factory.Sequence(lambda n: f"Feed {n}")
    description = ""
    feed_type = SupportedFeedType.rss

    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Feed


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


class FeedUpdateFactory(DjangoModelFactory):
    success = True
    feed_etag = ""
    feed_last_modified = None

    feed = factory.SubFactory(FeedFactory)

    class Meta:
        model = FeedUpdate


class ReadingListFactory(DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Reading list {n}")
    slug = factory.Sequence(lambda n: f"reading-list-{n}")

    user = factory.SubFactory(UserFactory)

    class Meta:
        model = ReadingList


class TagFactory(DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Tag {n}")
    slug = factory.Sequence(lambda n: f"tag-{n}")

    class Meta:
        model = Tag
