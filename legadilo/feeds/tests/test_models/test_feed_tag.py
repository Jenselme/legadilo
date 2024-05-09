import pytest

from legadilo.feeds.models import FeedTag
from legadilo.feeds.tests.factories import FeedFactory
from legadilo.reading.tests.factories import TagFactory


@pytest.mark.django_db()
class TestFeedTagManager:
    def test_associate_feed_with_tags(self):
        feed = FeedFactory()
        tag1 = TagFactory(user=feed.user)
        tag2 = TagFactory(user=feed.user)
        FeedTag.objects.create(feed=feed, tag=tag1)

        FeedTag.objects.associate_feed_with_tags(feed, [tag1, tag2])

        assert FeedTag.objects.count() == 2
