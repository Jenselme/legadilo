from datetime import UTC, datetime
from http import HTTPStatus

import pytest
from django.core.paginator import Paginator
from django.urls import reverse

from legadilo.feeds import constants
from legadilo.feeds.models import ArticleTag
from legadilo.feeds.tests.factories import ArticleFactory, ReadingListFactory, TagFactory


@pytest.mark.django_db()
class TestReadingListWithArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user, other_user):
        self.default_reading_list = ReadingListFactory(
            is_default=True, user=user, read_status=constants.ReadStatus.ONLY_UNREAD, order=0
        )
        self.reading_list = ReadingListFactory(user=user, order=10, enable_reading_on_scroll=True)
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
        ArticleFactory(feed__user=other_user)

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

    def test_cannot_access_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.reading_list_url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_default_view(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(10):
            response = logged_in_sync_client.get(self.default_reading_list_url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["page_title"] == self.default_reading_list.name
        assert response.context["reading_lists"] == [self.default_reading_list, self.reading_list]
        assert response.context["displayed_reading_list_id"] == self.default_reading_list.id
        assert response.context["js_cfg"] == {"is_reading_on_scroll_enabled": False}
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [self.unread_article]

    def test_reading_list_view(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(10):
            response = logged_in_sync_client.get(self.reading_list_url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["page_title"] == self.reading_list.name
        assert response.context["displayed_reading_list_id"] == self.reading_list.id
        assert response.context["reading_lists"] == [self.default_reading_list, self.reading_list]
        assert response.context["js_cfg"] == {"is_reading_on_scroll_enabled": True}
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [
            self.read_article,
            self.unread_article,
        ]


@pytest.mark.django_db()
class TestTagWithArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.tag_to_display = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        self.url = reverse("feeds:tag_with_articles", kwargs={"tag_slug": self.tag_to_display.slug})
        self.article_in_list = ArticleFactory(feed__user=user)
        ArticleTag.objects.create(tag=self.tag_to_display, article=self.article_in_list)
        other_article = ArticleFactory(feed__user=user)
        ArticleTag.objects.create(tag=other_tag, article=other_article)

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_access_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_tag_with_articles_view(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(7):
            response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["page_title"] == f"Articles with tag '{self.tag_to_display.name}'"
        assert response.context["displayed_reading_list_id"] is None
        assert response.context["reading_lists"] == []
        assert response.context["js_cfg"] == {}
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [
            self.article_in_list,
        ]
