from datetime import UTC, datetime

import pytest
import time_machine
from asgiref.sync import async_to_sync

from legadilo.feeds.models import FeedUpdate

from ..factories import FeedFactory, FeedUpdateFactory


@pytest.mark.django_db()
class TestFeedUpdateManager:
    def test_get_latest_for_feed(self):
        feed = FeedFactory()
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed=feed)
        with time_machine.travel(datetime(2023, 12, 31, 11, tzinfo=UTC)):
            latest_feed_update = FeedUpdateFactory(feed=feed)
        with time_machine.travel(datetime(2023, 12, 30, 12, tzinfo=UTC)):
            FeedUpdateFactory()
            FeedUpdateFactory(feed=feed, success=False)

        latest = async_to_sync(FeedUpdate.objects.get_latest_success_for_feed)(feed)

        assert latest.pk == latest_feed_update.pk
        assert latest.created_at == datetime(2023, 12, 31, 11, tzinfo=UTC)

    def test_must_not_disable_feed_no_error(self):
        feed = FeedFactory()
        FeedUpdateFactory(feed=feed)

        assert not FeedUpdate.objects.must_disable_feed(feed)

    def test_must_disable_feed(self):
        feed = FeedFactory()
        FeedUpdateFactory(feed=feed, success=False)

        assert FeedUpdate.objects.must_disable_feed(feed)

    def test_must_not_disable_feed_an_update_succeeded(self):
        feed = FeedFactory()
        FeedUpdateFactory(feed=feed, success=False)
        FeedUpdateFactory(feed=feed, success=True)
        FeedUpdateFactory(feed=feed, success=False)

        assert not FeedUpdate.objects.must_disable_feed(feed)
