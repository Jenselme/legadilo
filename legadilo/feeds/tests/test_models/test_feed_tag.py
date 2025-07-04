# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from legadilo.feeds.models import FeedTag
from legadilo.feeds.tests.factories import FeedFactory
from legadilo.reading.models import Tag
from legadilo.reading.tests.factories import TagFactory


@pytest.mark.django_db
class TestFeedTagManager:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.feed = FeedFactory()
        self.tag1 = TagFactory(user=self.feed.user)
        self.tag2 = TagFactory(user=self.feed.user)

    def test_get_selected_values(self):
        self.feed.tags.add(self.tag1)

        selected_tag = self.feed.feed_tags.get_selected_values()

        assert selected_tag == [self.tag1.slug]

    def test_associate_feed_with_tags(self):
        FeedTag.objects.create(feed=self.feed, tag=self.tag1)

        FeedTag.objects.associate_feed_with_tags(self.feed, [self.tag1, self.tag2])

        assert FeedTag.objects.count() == 2

    def test_associate_feed_with_tag_slugs(self):
        self.feed.tags.add(self.tag1)

        FeedTag.objects.associate_feed_with_tag_slugs(self.feed, [self.tag2.slug, "New tag"])

        assert FeedTag.objects.count() == 3
        assert self.feed.feed_tags.get_selected_values() == [
            "new-tag",
            self.tag1.slug,
            self.tag2.slug,
        ]

    def test_associate_feed_with_tag_slugs_clear_existing(self):
        self.feed.tags.add(self.tag1, self.tag2)

        FeedTag.objects.associate_feed_with_tag_slugs(
            self.feed, [self.tag2.slug, "New tag"], clear_existing=True
        )

        assert FeedTag.objects.count() == 2
        assert self.feed.feed_tags.get_selected_values() == [
            "new-tag",
            self.tag2.slug,
        ]
        assert Tag.objects.count() == 3
