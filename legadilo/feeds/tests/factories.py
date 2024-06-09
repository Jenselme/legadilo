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

import factory
from factory.django import DjangoModelFactory

from legadilo.feeds.constants import SupportedFeedType
from legadilo.feeds.models import FeedUpdate
from legadilo.users.tests.factories import UserFactory

from .. import constants
from ..models import Feed, FeedCategory


class FeedCategoryFactory(DjangoModelFactory):
    title = factory.Sequence(lambda n: f"Feed category {n}")
    slug = factory.Sequence(lambda n: f"feed-category-{n}")
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = FeedCategory


class FeedFactory(DjangoModelFactory):
    feed_url = factory.Sequence(lambda n: f"https://example.com/feeds/{n}.xml")
    site_url = "https://example.com"
    title = factory.Sequence(lambda n: f"Feed {n}")
    description = ""
    feed_type = SupportedFeedType.rss

    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Feed


class FeedUpdateFactory(DjangoModelFactory):
    status = constants.FeedUpdateStatus.SUCCESS
    feed_etag = ""
    feed_last_modified = None

    feed = factory.SubFactory(FeedFactory)

    class Meta:
        model = FeedUpdate
