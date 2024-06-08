# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
