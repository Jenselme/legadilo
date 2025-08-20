# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import UTC, datetime
from http import HTTPStatus

import httpx
import pytest
import time_machine
from django.core.management import call_command

from legadilo.feeds.models import FeedUpdate
from legadilo.feeds.tests.factories import FeedFactory, FeedUpdateFactory
from legadilo.reading.models import Article
from legadilo.users.models import Notification
from legadilo.utils.time_utils import utcdt

from ... import constants
from ..fixtures import get_feed_fixture_content


@pytest.mark.django_db
class TestUpdateFeedsCommand:
    def test_update_feed_command_no_feed(self):
        call_command("update_feeds")

    def test_update_feed_command(self, httpx_mock, django_assert_num_queries):
        feed_url = "http://example.com/feed/rss.xml"
        other_feed_url = "http://example.com/feed/atom.xml"
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed__feed_url=feed_url)
        httpx_mock.add_response(url=feed_url, content=get_feed_fixture_content("sample_rss.xml"))
        feed_without_feed_update = FeedFactory(feed_url=other_feed_url)
        httpx_mock.add_response(
            url=other_feed_url, content=get_feed_fixture_content("sample_atom.xml")
        )

        with (
            time_machine.travel(datetime(2023, 12, 31, 12, 0, tzinfo=UTC), tick=False),
        ):
            call_command("update_feeds")

        assert Article.objects.count() == 3
        assert FeedUpdate.objects.count() == 3
        feed_update = FeedUpdate.objects.first()
        assert feed_update is not None
        assert feed_update.created_at == datetime(2023, 12, 31, 12, 0, tzinfo=UTC)
        assert feed_update.status == constants.FeedUpdateStatus.SUCCESS
        assert not feed_update.feed_etag
        assert feed_update.feed_last_modified is None
        assert feed_without_feed_update.feed_updates.count() == 1

    def test_update_feed_command_feed_not_modified(self, httpx_mock, django_assert_num_queries):
        feed_url = "http://example.com/feed/rss.xml"
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed__feed_url=feed_url)
        httpx_mock.add_response(status_code=HTTPStatus.NOT_MODIFIED, url=feed_url)

        with (
            time_machine.travel(datetime(2023, 12, 31, 12, 0, tzinfo=UTC), tick=False),
        ):
            call_command("update_feeds")

        assert Article.objects.count() == 0
        assert FeedUpdate.objects.count() == 2
        feed_update = FeedUpdate.objects.first()
        assert feed_update is not None
        assert feed_update.created_at == datetime(2023, 12, 31, 12, 0, tzinfo=UTC)
        assert feed_update.status == constants.FeedUpdateStatus.NOT_MODIFIED

    def test_update_feed_command_http_error(self, httpx_mock, django_assert_num_queries):
        feed_url = "http://example.com/feed/rss.xml"
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed__feed_url=feed_url)
        httpx_mock.add_exception(httpx.HTTPError("Some error"), url=feed_url)

        with (
            time_machine.travel(datetime(2023, 12, 31, 12, 0, tzinfo=UTC), tick=False),
        ):
            call_command("update_feeds")

        assert Article.objects.count() == 0
        assert FeedUpdate.objects.count() == 2
        feed_update = FeedUpdate.objects.select_related("feed").first()
        assert feed_update is not None
        assert feed_update.created_at == datetime(2023, 12, 31, 12, 0, tzinfo=UTC)
        assert feed_update.status == constants.FeedUpdateStatus.FAILURE
        assert feed_update.error_message == "HTTPError(Some error)"
        assert feed_update.technical_debug_data == {"request": None, "response": None}
        assert not feed_update.feed_etag
        assert feed_update.feed_last_modified is None
        assert feed_update.feed.enabled

    def test_update_feed_command_http_error_must_disable_feed(
        self, httpx_mock, mocker, django_assert_num_queries
    ):
        feed_url = "http://example.com/feed/rss.xml"
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed__feed_url=feed_url)
        httpx_mock.add_exception(httpx.HTTPError("Some error"), url=feed_url)
        mocker.patch.object(
            FeedUpdate.objects,
            "must_disable_feed",
            return_value=True,
        )

        with (
            time_machine.travel(datetime(2023, 12, 31, 12, 0, tzinfo=UTC), tick=False),
        ):
            call_command("update_feeds")

        assert Article.objects.count() == 0
        assert FeedUpdate.objects.count() == 2
        feed_update = FeedUpdate.objects.select_related("feed").first()
        assert feed_update is not None
        assert feed_update.created_at == datetime(2023, 12, 31, 12, 0, tzinfo=UTC)
        assert feed_update.status == constants.FeedUpdateStatus.FAILURE
        assert feed_update.error_message == "HTTPError(Some error)"
        assert not feed_update.feed_etag
        assert feed_update.feed_last_modified is None
        assert not feed_update.feed.enabled
        assert (
            feed_update.feed.disabled_reason
            == "The server failed too many times to fetch the feed."
        )
        assert feed_update.feed.disabled_at == utcdt(2023, 12, 31, 12)
        assert Notification.objects.count() == 1
