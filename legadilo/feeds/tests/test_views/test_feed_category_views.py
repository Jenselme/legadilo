#  SPDX-FileCopyrightText: 2026 Legadilo contributors
#
#  SPDX-License-Identifier: AGPL-3.0-or-later
from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.feeds.tests.factories import FeedCategoryFactory


@pytest.mark.django_db
class TestFeedCategoriesAutocompleteView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("feeds:feed_category_autocomplete")
        self.category = FeedCategoryFactory(user=user, title="My category")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("account_login") + f"?next={self.url}"

    def test_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url, data={"query": "cat"})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == []

    def test_list(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url, data={"query": "cat"})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == [{"value": self.category.slug, "label": self.category.title}]

    def test_list_no_query(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.json() == []
