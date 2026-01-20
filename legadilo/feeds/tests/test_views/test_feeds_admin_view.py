# SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.conftest import assert_redirected_to_login_page
from legadilo.feeds import constants
from legadilo.feeds.models import Feed, FeedArticle
from legadilo.feeds.tests.factories import FeedCategoryFactory, FeedFactory
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory, TagFactory


@pytest.mark.django_db
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

        assert_redirected_to_login_page(response)

    def test_feeds_admin_view_no_data(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/feeds_admin.html"
        assert response.context_data["feeds_by_categories"] == {}

    def test_feeds_admin_view_data(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/feeds_admin.html"
        assert response.context_data["feeds_by_categories"] == {
            None: [self.feed_without_category],
            self.feed_category.title: [self.feed, self.feed_without_slug],
        }

    def test_feed_admin_with_search(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url, {"q": self.feed.title})

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/feeds_admin.html"
        assert response.context_data["feeds_by_categories"] == {
            self.feed_category.title: [self.feed],
        }


class TestEditFeedView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.feed = FeedFactory(user=user, refresh_delay=constants.FeedRefreshDelays.HOURLY)
        self.feed_category = FeedCategoryFactory(user=user)
        self.url = reverse("feeds:edit_feed", kwargs={"feed_id": self.feed.id})

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert_redirected_to_login_page(response)

    def test_edit_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_feed(self, user, logged_in_sync_client, django_assert_num_queries):
        article = ArticleFactory(user=user)
        FeedArticle.objects.create(feed=self.feed, article=article)

        with django_assert_num_queries(15):
            response = logged_in_sync_client.post(self.url, data={"delete": ""})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("feeds:feeds_admin")
        assert Feed.objects.count() == 0
        assert Article.objects.count() > 0

    def test_disable_feed(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(11):
            response = logged_in_sync_client.post(self.url, data={"disable": ""})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("feeds:feeds_admin")
        self.feed.refresh_from_db()
        assert not self.feed.enabled
        assert self.feed.disabled_reason == "Manually disabled"

    def test_enable_feed(self, logged_in_sync_client, django_assert_num_queries):
        self.feed.disable()
        self.feed.save()

        with django_assert_num_queries(11):
            response = logged_in_sync_client.post(self.url, data={"enable": ""})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("feeds:feeds_admin")
        self.feed.refresh_from_db()
        assert self.feed.enabled
        assert not self.feed.disabled_reason

    def test_update_feed(self, user, logged_in_sync_client, django_assert_num_queries):
        tag1 = TagFactory(user=user)
        self.feed.tags.add(tag1)

        with django_assert_num_queries(25):
            response = logged_in_sync_client.post(
                self.url,
                data={
                    "category": self.feed_category.slug,
                    "refresh_delay": constants.FeedRefreshDelays.ON_MONDAYS,
                    "article_retention_time": 7,
                    "tags": ["new-tag"],
                    "save": "",
                },
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("feeds:feeds_admin")
        self.feed.refresh_from_db()
        assert self.feed.category == self.feed_category
        assert self.feed.refresh_delay == constants.FeedRefreshDelays.ON_MONDAYS
        assert self.feed.article_retention_time == 7
        assert list(self.feed.feed_tags.get_selected_values()) == ["new-tag"]

    def test_update_feed_continue_edition(self, user, logged_in_sync_client):
        response = logged_in_sync_client.post(
            self.url,
            data={
                "category": self.feed_category.slug,
                "refresh_delay": constants.FeedRefreshDelays.ON_MONDAYS,
                "article_retention_time": 7,
                "save-continue-edition": "",
            },
        )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/edit_feed.html"

    def test_remove_category(self, logged_in_sync_client):
        self.feed.category = self.feed_category
        self.feed.save()

        response = logged_in_sync_client.post(
            self.url,
            data={
                "category": "",
                "tags": [],
                "refresh_delay": constants.FeedRefreshDelays.HOURLY,
                "article_retention_time": 7,
            },
        )

        assert response.status_code == HTTPStatus.OK
        self.feed.refresh_from_db()
        assert self.feed.category is None
