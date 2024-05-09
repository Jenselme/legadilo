import factory
from factory.django import DjangoModelFactory

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.models import FeedUpdate
from legadilo.users.tests.factories import UserFactory

from .. import constants
from ..models import Feed, FeedCategory


class FeedCategoryFactory(DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Feed category {n}")
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


class FeedUpdateFactory(DjangoModelFactory):
    status = constants.FeedUpdateStatus.SUCCESS
    feed_etag = ""
    feed_last_modified = None

    feed = factory.SubFactory(FeedFactory)

    class Meta:
        model = FeedUpdate
