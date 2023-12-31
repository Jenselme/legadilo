from datetime import UTC, datetime
from http import HTTPStatus

import httpx
import pytest
import time_machine
from django.core.management import call_command

from legadilo.feeds.models import Article, FeedUpdate
from legadilo.feeds.tests.factories import FeedUpdateFactory

from ..fixtures import SAMPLE_RSS_FEED


@pytest.mark.django_db(transaction=True)
class TestUpdateFeedsCommand:
    def test_update_feed_command_no_feed(self):
        call_command("update_feeds")

    def test_update_feed_command(self, httpx_mock):
        feed_url = "http://example.com/feed/rss.xml"
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed__feed_url=feed_url)
        httpx_mock.add_response(url=feed_url, content=SAMPLE_RSS_FEED)

        with time_machine.travel(datetime(2023, 12, 31, tzinfo=UTC), tick=False):
            call_command("update_feeds")

        assert Article.objects.count() == 1
        assert FeedUpdate.objects.count() == 2
        feed_update = FeedUpdate.objects.first()
        assert feed_update is not None
        assert feed_update.created_at == datetime(2023, 12, 31, tzinfo=UTC)
        assert feed_update.success
        assert not feed_update.feed_etag
        assert feed_update.feed_last_modified is None

    def test_update_feed_command_feed_not_modified(self, httpx_mock):
        feed_url = "http://example.com/feed/rss.xml"
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed__feed_url=feed_url)
        httpx_mock.add_response(status_code=HTTPStatus.NOT_MODIFIED, url=feed_url)

        with time_machine.travel(datetime(2023, 12, 31, tzinfo=UTC), tick=False):
            call_command("update_feeds")

        assert Article.objects.count() == 0
        assert FeedUpdate.objects.count() == 1

    def test_update_feed_command_http_error(self, httpx_mock):
        feed_url = "http://example.com/feed/rss.xml"
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed__feed_url=feed_url)
        httpx_mock.add_exception(httpx.HTTPError("Some error"), url=feed_url)

        with time_machine.travel(datetime(2023, 12, 31, tzinfo=UTC), tick=False):
            call_command("update_feeds")

        assert Article.objects.count() == 0
        assert FeedUpdate.objects.count() == 2
        feed_update = FeedUpdate.objects.select_related("feed").first()
        assert feed_update is not None
        assert feed_update.created_at == datetime(2023, 12, 31, tzinfo=UTC)
        assert not feed_update.success
        assert feed_update.error_message == "Some error"
        assert not feed_update.feed_etag
        assert feed_update.feed_last_modified is None
        assert feed_update.feed.enabled

    def test_update_feed_command_http_error_must_disable_feed(self, httpx_mock, mocker):
        feed_url = "http://example.com/feed/rss.xml"
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed__feed_url=feed_url)
        httpx_mock.add_exception(httpx.HTTPError("Some error"), url=feed_url)
        mocker.patch.object(
            FeedUpdate.objects,
            "must_disable_feed",
            return_value=True,
        )

        with time_machine.travel(datetime(2023, 12, 31, tzinfo=UTC), tick=False):
            call_command("update_feeds")

        assert Article.objects.count() == 0
        assert FeedUpdate.objects.count() == 2
        feed_update = FeedUpdate.objects.select_related("feed").first()
        assert feed_update is not None
        assert feed_update.created_at == datetime(2023, 12, 31, tzinfo=UTC)
        assert not feed_update.success
        assert feed_update.error_message == "Some error"
        assert not feed_update.feed_etag
        assert feed_update.feed_last_modified is None
        assert not feed_update.feed.enabled
        assert feed_update.feed.disabled_reason == "We failed too many times to fetch the feed"
