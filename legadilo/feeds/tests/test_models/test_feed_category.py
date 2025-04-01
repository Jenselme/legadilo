# Legadilo
# Copyright (C) 2023-2025 by Legadilo contributors.
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

from legadilo.feeds.models import FeedCategory
from legadilo.feeds.tests.factories import FeedCategoryFactory
from legadilo.utils.testing import serialize_for_snapshot


@pytest.mark.django_db
class TestFeedCategoryQuerySet:
    def test_for_user(self, user):
        feed_category = FeedCategoryFactory(user=user)
        FeedCategoryFactory()

        categories_for_user = FeedCategory.objects.get_queryset().for_user(user)

        assert list(categories_for_user) == [feed_category]


@pytest.mark.django_db
class TestFeedCategoryManager:
    def test_get_all_choices(self, user):
        feed_category = FeedCategoryFactory(user=user)
        FeedCategoryFactory()

        categories_for_user = FeedCategory.objects.get_all_choices(user)

        assert list(categories_for_user) == [
            ("", "None"),
            (feed_category.slug, feed_category.title),
        ]

    def test_get_first_for_user(self, user, other_user):
        feed_category_user = FeedCategoryFactory(user=user, title="Slug", slug="slug")
        FeedCategoryFactory(user=other_user, title="Slug", slug="slug")

        found_category = FeedCategory.objects.get_first_for_user(user, "slug")
        inexistant_slug = FeedCategory.objects.get_first_for_user(user, "some trash")

        assert found_category == feed_category_user
        assert inexistant_slug is None

    def test_export(self, user, other_user, snapshot, django_assert_num_queries):
        feed_category_user = FeedCategoryFactory(user=user, id=1, title="Slug", slug="slug")
        FeedCategoryFactory(user=other_user, title="Slug", slug="slug")

        with django_assert_num_queries(1):
            exports = FeedCategory.objects.export(user)

        assert len(exports) == 1
        assert exports[0]["category_id"] == feed_category_user.id
        snapshot.assert_match(serialize_for_snapshot(exports), "categories.json")
