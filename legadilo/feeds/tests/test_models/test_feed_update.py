from datetime import UTC, datetime

import pytest
import time_machine
from asgiref.sync import sync_to_async

from legadilo.feeds.models import FeedUpdate

from ..factories import FeedFactory, FeedUpdateFactory


@pytest.mark.django_db(transaction=True)
class TestFeedUpdateManager:
    @pytest.mark.asyncio()
    async def test_get_latest_for_feed(self):
        feed = await sync_to_async(FeedFactory)()
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            await sync_to_async(FeedUpdateFactory)(feed=feed)
        with time_machine.travel(datetime(2023, 12, 31, 11, tzinfo=UTC)):
            latest_feed_update = await sync_to_async(FeedUpdateFactory)(feed=feed)
        with time_machine.travel(datetime(2023, 12, 30, 12, tzinfo=UTC)):
            await sync_to_async(FeedUpdateFactory)()
            await sync_to_async(FeedUpdateFactory)(feed=feed, success=False)

        latest = await FeedUpdate.objects.get_latest_success_for_feed(feed)

        assert latest.pk == latest_feed_update.pk
        assert latest.created_at == datetime(2023, 12, 31, 11, tzinfo=UTC)
