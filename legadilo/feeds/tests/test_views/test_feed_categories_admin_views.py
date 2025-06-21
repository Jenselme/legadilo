# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

import pytest
from django.contrib.messages import DEFAULT_LEVELS, get_messages
from django.contrib.messages.storage.base import Message
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

    def test_create_category(
        self, logged_in_sync_client, user, other_user, django_assert_num_queries
    ):
        with django_assert_num_queries(8):
            response = logged_in_sync_client.post(self.url, data={"title": "My category"})

        assert response.status_code == HTTPStatus.FOUND
        feed_category = FeedCategory.objects.get(user=user)
        assert response["Location"] == f"/feeds/categories/{feed_category.id}/"
        assert feed_category.user == user
        assert feed_category.title == "My category"

    def test_create_duplicated_category(self, logged_in_sync_client, user):
        category = FeedCategoryFactory(title="My category", slug="my-category", user=user)

        response = logged_in_sync_client.post(self.url, data={"title": category.title})

        assert response.status_code == HTTPStatus.CONFLICT
        assert FeedCategory.objects.count() == 1
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message=f"A category with title '{category.title}' already exists.",
            )
        ]

    def test_create_category_invalid_form(self, logged_in_sync_client, user, other_user):
        response = logged_in_sync_client.post(self.url, data={})

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert FeedCategory.objects.count() == 0
        assert response.template_name == "feeds/edit_feed_category.html"
        assert response.context_data["form"].errors == {"title": ["This field is required."]}


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
