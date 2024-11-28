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
from typing import Any

import httpx
import pytest
from django.urls import reverse

from legadilo.feeds import constants
from legadilo.feeds.models import Feed, FeedCategory
from legadilo.feeds.tests.factories import FeedCategoryFactory, FeedDataFactory, FeedFactory
from legadilo.reading.tests.factories import TagFactory
from legadilo.utils.testing import serialize_for_snapshot
from legadilo.utils.time_utils import utcdt


def _prepare_feed_for_snapshot(data: dict[str, Any], feed: Feed) -> dict[str, Any]:
    data = data.copy()
    assert data["id"] == feed.id
    assert data["slug"] == feed.slug
    assert data["title"] == feed.title
    assert data["feed_url"] == feed.feed_url
    assert (feed.category_id is None and data["category"] is None) or (
        feed.category_id == data["category"]["id"]
    )

    data["id"] = 1
    data["slug"] = "feed-slug"
    data["title"] = "Feed title"
    data["feed_url"] = "https://example.com/feed.rss"
    if data.get("category"):
        data["category"]["id"] = 10
        data["category"]["title"] = "Category title"
        data["category"]["slug"] = "category-slug"

    return data


@pytest.mark.django_db
class TestListCategoriesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("api-1.0.0:list_feed_categories")
        self.feed_category = FeedCategoryFactory(user=user)

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_list_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"count": 0, "items": []}

    def test_list(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {
            "count": 1,
            "items": [
                {
                    "id": self.feed_category.id,
                    "slug": self.feed_category.slug,
                    "title": self.feed_category.title,
                }
            ],
        }


@pytest.mark.django_db
class TestCreateCategoryView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("api-1.0.0:create_feed_category")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_create(self, logged_in_sync_client, user, django_assert_num_queries):
        with django_assert_num_queries(9):
            response = logged_in_sync_client.post(
                self.url, {"title": "Test category"}, content_type="application/json"
            )

        assert response.status_code == HTTPStatus.CREATED
        assert FeedCategory.objects.count() == 1
        feed_category = FeedCategory.objects.get()
        assert feed_category.title == "Test category"
        assert feed_category.user == user
        assert response.json() == {
            "id": feed_category.id,
            "slug": feed_category.slug,
            "title": feed_category.title,
        }

    def test_create_duplicate(self, user, logged_in_sync_client):
        feed_category = FeedCategoryFactory(user=user)

        response = logged_in_sync_client.post(
            self.url, {"title": feed_category.title}, content_type="application/json"
        )

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json() == {"detail": "A category with this title already exists."}
        assert FeedCategory.objects.count() == 1


@pytest.mark.django_db
class TestGetCategoryView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed_category = FeedCategoryFactory(user=user)
        self.url = reverse(
            "api-1.0.0:get_feed_category", kwargs={"category_id": self.feed_category.id}
        )

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {
            "id": self.feed_category.id,
            "slug": self.feed_category.slug,
            "title": self.feed_category.title,
        }


@pytest.mark.django_db
class TestUpdateCategoryView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed_category = FeedCategoryFactory(user=user)
        self.url = reverse(
            "api-1.0.0:update_feed_category", kwargs={"category_id": self.feed_category.id}
        )

    def test_not_logged_in(self, client):
        response = client.patch(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_update_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.patch(
            self.url, {"title": "New title"}, content_type="application/json"
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.patch(
                self.url, {"title": "New title"}, content_type="application/json"
            )

        assert response.status_code == HTTPStatus.OK
        self.feed_category.refresh_from_db()
        assert self.feed_category.title == "New title"
        assert response.json() == {
            "id": self.feed_category.id,
            "slug": self.feed_category.slug,
            "title": "New title",
        }


@pytest.mark.django_db
class TestDeleteCategoryView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed_category = FeedCategoryFactory(user=user)
        self.url = reverse(
            "api-1.0.0:delete_feed_category", kwargs={"category_id": self.feed_category.id}
        )

    def test_not_logged_in(self, client):
        response = client.delete(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_delete_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.delete(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(8):
            response = logged_in_sync_client.delete(self.url)

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert FeedCategory.objects.count() == 0


@pytest.mark.django_db
class TestListFeedsView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed = FeedFactory(user=user)
        self.url = reverse("api-1.0.0:list_feeds")

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_list_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"count": 0, "items": []}

    def test_list(self, logged_in_sync_client, django_assert_num_queries, snapshot):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data["items"]) == 1
        data["items"][0] = _prepare_feed_for_snapshot(data["items"][0], self.feed)
        snapshot.assert_match(serialize_for_snapshot(data), "feeds.json")


@pytest.mark.django_db
class TestSubscribeToFeedView:
    @pytest.fixture(autouse=True)
    def _setup_data(self):
        self.url = reverse("api-1.0.0:subscribe_to_feed")

    def test_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_subscribe_to_feed_invalid_url(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(
            self.url, {"feed_url": "toto"}, content_type="application/json"
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {
                    "ctx": {"error": "toto is not a valid url"},
                    "loc": ["body", "payload", "feed_url"],
                    "msg": "Value error, toto is not a valid url",
                    "type": "value_error",
                }
            ]
        }

    def test_subscribe_to_feed_with_just_url(
        self, user, logged_in_sync_client, mocker, django_assert_num_queries, snapshot
    ):
        feed_url = "https://example.com/feed.rss"
        mocker.patch(
            "legadilo.feeds.api.get_feed_data", return_value=FeedDataFactory(feed_url=feed_url)
        )

        with django_assert_num_queries(19):
            response = logged_in_sync_client.post(
                self.url, {"feed_url": feed_url}, content_type="application/json"
            )

        assert response.status_code == HTTPStatus.CREATED
        assert Feed.objects.count() == 1
        feed = Feed.objects.get()
        assert feed.feed_url == feed_url
        assert feed.category is None
        assert feed.user == user
        snapshot.assert_match(
            serialize_for_snapshot(_prepare_feed_for_snapshot(response.json(), feed)), "feed.json"
        )

    def test_subscribe_to_feed(
        self, user, logged_in_sync_client, mocker, django_assert_num_queries, snapshot
    ):
        feed_url = "https://example.com/feed.rss"
        mocker.patch(
            "legadilo.feeds.api.get_feed_data", return_value=FeedDataFactory(feed_url=feed_url)
        )
        category = FeedCategoryFactory(user=user)
        existing_tag = TagFactory(user=user)

        with django_assert_num_queries(23):
            response = logged_in_sync_client.post(
                self.url,
                {
                    "feed_url": feed_url,
                    "refresh_delay": constants.FeedRefreshDelays.HOURLY.value,
                    "article_retention_time": 100,
                    "category_id": category.id,
                    "tags": ["", "<p>Some tag</p>", existing_tag.slug],
                    "open_original_link_by_default": True,
                },
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.CREATED
        assert Feed.objects.count() == 1
        feed = Feed.objects.get()
        assert list(feed.tags.values_list("title", flat=True)) == ["Some tag", existing_tag.title]
        assert feed.user == user
        snapshot.assert_match(
            serialize_for_snapshot(_prepare_feed_for_snapshot(response.json(), feed)), "feed.json"
        )

    def test_subscribe_to_feed_invalid_category(self, logged_in_sync_client):
        response = logged_in_sync_client.post(
            self.url,
            {"feed_url": "https://example.com/feed.rss", "category_id": 0},
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [{"category_id": "We failed to find the category with id: 0"}]
        }
        assert FeedCategory.objects.count() == 0

    def test_subscribe_to_already_subscribed_feed(self, user, logged_in_sync_client, mocker):
        feed_url = "https://example.com/feed.rss"
        mocker.patch(
            "legadilo.feeds.api.get_feed_data", return_value=FeedDataFactory(feed_url=feed_url)
        )
        FeedFactory(user=user, feed_url=feed_url)

        response = logged_in_sync_client.post(
            self.url, {"feed_url": feed_url}, content_type="application/json"
        )

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json() == {"detail": "You are already subscribed to this feed"}
        assert Feed.objects.count() == 1

    def test_subscribe_to_feed_but_error_occurred(self, user, logged_in_sync_client, mocker):
        mocker.patch("legadilo.feeds.api.get_feed_data", side_effect=httpx.HTTPError("Kaboom!"))

        response = logged_in_sync_client.post(
            self.url, {"feed_url": "https://example.com/feed.rss"}, content_type="application/json"
        )

        assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
        assert response.json() == {
            "detail": "We failed to access or parse the feed you supplied. Please make "
            "sure it is accessible and valid."
        }


@pytest.mark.django_db
class TestGetFeedView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed = FeedFactory(user=user)
        self.url = reverse("api-1.0.0:get_feed", kwargs={"feed_id": self.feed.id})

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get(self, logged_in_sync_client, django_assert_num_queries, snapshot):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK

        snapshot.assert_match(
            serialize_for_snapshot(_prepare_feed_for_snapshot(response.json(), self.feed)),
            "feed.json",
        )


@pytest.mark.django_db
class TestUpdateFeedView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed_category = FeedCategoryFactory(user=user)
        self.other_feed_category = FeedCategoryFactory(user=user)
        self.feed = FeedFactory(user=user, category=self.feed_category)
        self.url = reverse("api-1.0.0:update_feed", kwargs={"feed_id": self.feed.id})

    def test_not_logged_in(self, client):
        response = client.patch(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_update_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.patch(
            self.url, {"category_id": self.other_feed_category.id}, content_type="application/json"
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_category(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(8):
            response = logged_in_sync_client.patch(
                self.url,
                {"category_id": self.other_feed_category.id},
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.OK
        self.feed.refresh_from_db()
        assert self.feed.category_id == self.other_feed_category.id

    def test_unset_category(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(8):
            response = logged_in_sync_client.patch(
                self.url,
                {"category_id": None},
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.OK
        self.feed.refresh_from_db()
        assert self.feed.category_id is None

    def test_disable_feed_invalid_payload(self, logged_in_sync_client):
        response = logged_in_sync_client.patch(
            self.url,
            {"disabled_at": "2024-11-24 21:00:00Z"},
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json() == {
            "detail": [
                {
                    "ctx": {
                        "error": "You must supply none of disabled_reason and disabled_at "
                        "or both of them"
                    },
                    "loc": ["body", "payload"],
                    "msg": "Value error, You must supply none of disabled_reason and "
                    "disabled_at or both of them",
                    "type": "value_error",
                }
            ]
        }

    def test_update(self, logged_in_sync_client, django_assert_num_queries, snapshot):
        with django_assert_num_queries(8):
            response = logged_in_sync_client.patch(
                self.url,
                {
                    "refresh_delay": constants.FeedRefreshDelays.TWICE_A_WEEK,
                    "article_retention_time": 600,
                },
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.OK
        self.feed.refresh_from_db()
        assert not self.feed.open_original_link_by_default
        assert self.feed.enabled
        assert self.feed.refresh_delay == constants.FeedRefreshDelays.TWICE_A_WEEK
        assert self.feed.article_retention_time == 600
        snapshot.assert_match(
            serialize_for_snapshot(_prepare_feed_for_snapshot(response.json(), self.feed)),
            "feed.json",
        )

    def test_disable_feed(self, logged_in_sync_client):
        response = logged_in_sync_client.patch(
            self.url,
            {"disabled_at": "2024-11-24 21:00:00Z", "disabled_reason": "<p>Manually disabled</p>"},
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.OK
        self.feed.refresh_from_db()
        assert self.feed.disabled_at == utcdt(2024, 11, 24, 21)
        assert self.feed.disabled_reason == "Manually disabled"

    def test_reenable_feed(self, logged_in_sync_client):
        self.feed.disable("Manually disabled")
        self.feed.save()

        response = logged_in_sync_client.patch(
            self.url,
            {"disabled_at": None, "disabled_reason": None},
            content_type="application/json",
        )
        assert response.status_code == HTTPStatus.OK
        self.feed.refresh_from_db()
        assert self.feed.disabled_at is None
        assert not self.feed.disabled_reason

    def test_update_tags(self, logged_in_sync_client, user, django_assert_num_queries, snapshot):
        existing_tag = TagFactory(user=user, title="Tag to keep")
        tag_to_delete = TagFactory(user=user, title="Tag to delete")
        self.feed.tags.add(existing_tag, tag_to_delete)

        with django_assert_num_queries(18):
            response = logged_in_sync_client.patch(
                self.url,
                {
                    "tags": [existing_tag.slug, "", "<p>New tag</p>"],
                },
                content_type="application/json",
            )

        assert response.status_code == HTTPStatus.OK
        self.feed.refresh_from_db()
        assert list(self.feed.tags.all().values_list("title", flat=True)) == [
            "New tag",
            "Tag to keep",
        ]
        snapshot.assert_match(
            serialize_for_snapshot(_prepare_feed_for_snapshot(response.json(), self.feed)),
            "feed.json",
        )


@pytest.mark.django_db
class TestDeleteFeedView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed = FeedFactory(user=user)
        self.url = reverse("api-1.0.0:delete_feed", kwargs={"feed_id": self.feed.id})

    def test_not_logged_in(self, client):
        response = client.delete(self.url)

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_delete_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.delete(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(11):
            response = logged_in_sync_client.delete(self.url)

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert Feed.objects.count() == 0
