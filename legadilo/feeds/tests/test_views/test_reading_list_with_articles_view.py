from datetime import UTC, datetime
from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.feeds import constants
from legadilo.feeds.tests.factories import ArticleFactory, ReadingListFactory


@pytest.mark.django_db()
class TestReadingListWithArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.default_reading_list = ReadingListFactory(
            is_default=True, user=user, read_status=constants.ReadStatus.ONLY_UNREAD, order=0
        )
        self.reading_list = ReadingListFactory(user=user, order=10)
        self.default_reading_list_url = reverse("feeds:default_reading_list")
        self.reading_list_url = reverse(
            "feeds:reading_list", kwargs={"reading_list_slug": self.reading_list.slug}
        )

        self.read_article = ArticleFactory(
            is_read=True, published_at=datetime(2024, 3, 19, tzinfo=UTC), feed__user=user
        )
        self.unread_article = ArticleFactory(
            is_read=False, published_at=datetime(2024, 3, 10, tzinfo=UTC), feed__user=user
        )
        # Article of some other user.
        ArticleFactory()

    def test_not_logged_in(self, client):
        response = client.get(self.default_reading_list_url)
        assert response.status_code == HTTPStatus.FOUND
        assert (
            response["Location"]
            == reverse("account_login") + f"?next={self.default_reading_list_url}"
        )

        response = client.get(self.reading_list_url)
        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("account_login") + f"?next={self.reading_list_url}"

    def test_default_view(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.get(self.default_reading_list_url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["reading_lists"] == [self.default_reading_list, self.reading_list]
        assert response.context["displayed_reading_list"] == self.default_reading_list
        assert response.context["articles"] == [self.unread_article]

    def test_reading_list_view(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.get(self.reading_list_url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["reading_lists"] == [self.default_reading_list, self.reading_list]
        assert response.context["displayed_reading_list"] == self.reading_list
        assert response.context["articles"] == [self.read_article, self.unread_article]
