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

    @pytest.mark.asyncio()
    async def test_must_not_disable_feed_no_error(self):
        feed = await sync_to_async(FeedFactory)()
        await sync_to_async(FeedUpdateFactory)(feed=feed)

        assert not await FeedUpdate.objects.must_disable_feed(feed)

    @pytest.mark.asyncio()
    async def test_must_disable_feed(self):
        feed = await sync_to_async(FeedFactory)()
        await sync_to_async(FeedUpdateFactory)(feed=feed, success=False)

        assert await FeedUpdate.objects.must_disable_feed(feed)

    @pytest.mark.asyncio()
    async def test_must_not_disable_feed_an_update_succeeded(self):
        feed = await sync_to_async(FeedFactory)()
        await sync_to_async(FeedUpdateFactory)(feed=feed, success=False)
        await sync_to_async(FeedUpdateFactory)(feed=feed, success=True)
        await sync_to_async(FeedUpdateFactory)(feed=feed, success=False)

        assert not await FeedUpdate.objects.must_disable_feed(feed)
