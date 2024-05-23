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
