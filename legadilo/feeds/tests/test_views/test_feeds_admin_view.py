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

from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.feeds.tests.factories import FeedCategoryFactory, FeedFactory


@pytest.mark.django_db()
class TestFeedsAdminView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("feeds:feeds_admin")
        self.feed_without_category = FeedFactory(user=user, title="Some feed", slug="some-feed")
        self.feed_category = FeedCategoryFactory(
            user=user, title="Some category", slug="some-category"
        )
        self.feed = FeedFactory(
            user=user, title="Some other feed", slug="some-other-feed", category=self.feed_category
        )
        self.feed_without_slug = FeedFactory(
            user=user, title="No slug", slug="", category=self.feed_category
        )

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_feeds_admin_view_no_data(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/feeds_admin.html"
        assert response.context["feeds_by_categories"] == {}

    def test_feeds_admin_view_data(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/feeds_admin.html"
        assert response.context["feeds_by_categories"] == {
            None: [self.feed_without_category],
            self.feed_category.title: [self.feed, self.feed_without_slug],
        }
