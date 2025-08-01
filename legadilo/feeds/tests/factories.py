# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import factory
from factory.django import DjangoModelFactory

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.models import FeedArticle, FeedUpdate
from legadilo.users.tests.factories import UserFactory

from .. import constants
from ..models import Feed, FeedCategory
from ..services.feed_parsing import FeedData


class FeedCategoryFactory(DjangoModelFactory):
    title = factory.Sequence(lambda n: f"Feed category {n}")
    slug = factory.Sequence(lambda n: f"feed-category-{n}")
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = FeedCategory


class FeedFactory(DjangoModelFactory):
    feed_url = factory.Sequence(lambda n: f"https://example.com/feeds/{n}.xml")
    site_url = "https://example.com"
    title = factory.Sequence(lambda n: f"Feed {n}")
    description = ""
    feed_type = SupportedFeedType.rss

    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Feed


class FeedArticleFactory(DjangoModelFactory):
    feed_article_id = factory.Sequence(lambda n: f"article-{n}")

    class Meta:
        model = FeedArticle


class FeedUpdateFactory(DjangoModelFactory):
    status = constants.FeedUpdateStatus.SUCCESS
    feed_etag = ""
    feed_last_modified = None

    feed = factory.SubFactory(FeedFactory)

    class Meta:
        model = FeedUpdate


class FeedDataFactory(factory.DictFactory):
    feed_url = factory.Sequence(lambda n: f"https://example.com/feeds-{n}.rss")
    site_url = "https://example.com"
    title = factory.Sequence(lambda n: f"Feed {n}")
    description = "Some feed description"
    feed_type = SupportedFeedType.rss
    etag = ""
    last_modified = None
    articles = factory.ListFactory()

    class Meta:
        model = FeedData
