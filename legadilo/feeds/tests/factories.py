import factory
from factory.django import DjangoModelFactory

from legadilo.feeds.constants import SupportedFeedType

from ..models import Feed


class FeedFactory(DjangoModelFactory):
    feed_url = factory.Sequence(lambda n: f"https://example.com/feeds/{n}.xml")
    site_url = "https://example.com"
    title = factory.Sequence(lambda n: f"Feed {n}")
    description = ""
    feed_type = SupportedFeedType.rss

    class Meta:
        model = Feed
