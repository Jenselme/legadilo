# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import UTC, datetime

import pytest
import time_machine

from legadilo.feeds.models import FeedUpdate

from ... import constants
from ..factories import FeedFactory, FeedUpdateFactory


@pytest.mark.django_db
class TestFeedUpdateQuerySet:
    def test_only_latest(self):
        feed = FeedFactory()
        with time_machine.travel("2024-05-08 11:00:00"):
            latest_for_feed = FeedUpdateFactory(feed=feed)
        with time_machine.travel("2024-05-08 10:00:00"):
            FeedUpdateFactory(feed=feed)
            latest_for_other_feed = FeedUpdateFactory()

        latest = FeedUpdate.objects.get_queryset().only_latest()

        assert list(latest) == [{"id": latest_for_feed.id}, {"id": latest_for_other_feed.id}]

    def test_for_cleanup(self):
        feed = FeedFactory()
        other_feed = FeedFactory()
        with time_machine.travel("2024-03-15 12:00:00"):
            feed_update_to_cleanup = FeedUpdateFactory(feed=feed)
            # We only have this one, let's keep it.
            only_feed_update_for_feed = FeedUpdateFactory()

        with time_machine.travel("2024-05-01 12:00:00"):
            FeedUpdateFactory(feed=feed)
            FeedUpdateFactory(feed=other_feed)  # Too recent.

        with time_machine.travel("2024-05-03 12:00:00"):
            FeedUpdateFactory(feed=other_feed)  # Too recent.

        with time_machine.travel("2024-06-01 12:00:00"):
            feed_updates_to_cleanup = FeedUpdate.objects.get_queryset().for_cleanup({
                None,
                only_feed_update_for_feed.id,
            })

        assert list(feed_updates_to_cleanup) == [feed_update_to_cleanup]


@pytest.mark.django_db
class TestFeedUpdateManager:
    def test_get_latest_for_feed(self):
        feed = FeedFactory()
        with time_machine.travel(datetime(2023, 12, 30, tzinfo=UTC)):
            FeedUpdateFactory(feed=feed)
        with time_machine.travel(datetime(2023, 12, 31, 11, tzinfo=UTC)):
            latest_feed_update = FeedUpdateFactory(feed=feed)
        with time_machine.travel(datetime(2023, 12, 30, 12, tzinfo=UTC)):
            FeedUpdateFactory()
            FeedUpdateFactory(feed=feed, status=constants.FeedUpdateStatus.FAILURE)

        latest = FeedUpdate.objects.get_latest_success_for_feed_id(feed.id)

        assert latest.pk == latest_feed_update.pk
        assert latest.created_at == datetime(2023, 12, 31, 11, tzinfo=UTC)

    def test_must_not_disable_feed_no_error(self):
        feed = FeedFactory()
        FeedUpdateFactory(feed=feed)

        assert not FeedUpdate.objects.must_disable_feed(feed)

    def test_must_disable_feed(self):
        feed = FeedFactory()
        FeedUpdateFactory(feed=feed, status=constants.FeedUpdateStatus.FAILURE)

        assert FeedUpdate.objects.must_disable_feed(feed)

    def test_must_not_disable_feed_an_update_succeeded(self):
        feed = FeedFactory()
        FeedUpdateFactory(feed=feed, status=constants.FeedUpdateStatus.FAILURE)
        FeedUpdateFactory(feed=feed, status=constants.FeedUpdateStatus.SUCCESS)
        FeedUpdateFactory(feed=feed, status=constants.FeedUpdateStatus.FAILURE)

        assert not FeedUpdate.objects.must_disable_feed(feed)
