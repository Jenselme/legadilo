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

from legadilo.feeds.models import FeedCategory
from legadilo.feeds.tests.factories import FeedCategoryFactory


class TestCategoryFeedAdminView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("feeds:feed_category_admin")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"/accounts/login/?next={self.url}"

    def test_get_page(self, logged_in_sync_client, user, other_user):
        feed_category = FeedCategoryFactory(user=user)
        FeedCategoryFactory(user=other_user)

        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/feed_categories_admin.html"
        assert list(response.context_data["categories"]) == [feed_category]


class TestCreateFeedCategoryView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("feeds:create_feed_category")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"/accounts/login/?next={self.url}"

    def test_create_category(self, logged_in_sync_client, user):
        response = logged_in_sync_client.post(self.url, data={"title": "My category"})

        assert response.status_code == HTTPStatus.FOUND
        feed_category = FeedCategory.objects.get()
        assert response["Location"] == f"/feeds/categories/{feed_category.id}/"
        assert feed_category.user == user
        assert feed_category.title == "My category"


class TestEditFeedCategoryView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed_category = FeedCategoryFactory(user=user, title="Initial title")
        self.url = reverse(
            "feeds:edit_feed_category", kwargs={"category_id": self.feed_category.id}
        )

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"/accounts/login/?next={self.url}"

    def test_edit_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_edit_category(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, data={"title": "New title"})

        assert response.status_code == HTTPStatus.OK
        self.feed_category.refresh_from_db()
        assert self.feed_category.title == "New title"

    def test_delete_category(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, data={"title": "New title", "delete": ""})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("feeds:feed_category_admin")
        assert FeedCategory.objects.count() == 0
