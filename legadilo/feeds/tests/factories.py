from datetime import UTC, datetime

import factory
from factory.django import DjangoModelFactory

from legadilo.feeds.constants import SupportedFeedType
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
    authors = []
    contributors = []
    tags = []
    link = factory.Sequence(lambda n: f"https://example.com/article/{n}")
    published_at = datetime.now(tz=UTC)
    updated_at = datetime.now(tz=UTC)
    article_feed_id = factory.Sequence(lambda n: f"article-{n}")

    feed = factory.SubFactory(FeedFactory)

    class Meta:
        model = Article
