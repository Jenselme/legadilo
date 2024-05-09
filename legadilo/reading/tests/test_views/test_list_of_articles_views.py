from datetime import UTC, datetime
from http import HTTPStatus

import pytest
from django.core.paginator import Paginator
from django.urls import reverse

from legadilo.reading import constants
from legadilo.reading.models import ArticleTag
from legadilo.reading.tests.factories import ArticleFactory, ReadingListFactory, TagFactory
from legadilo.utils.time import utcnow


@pytest.mark.django_db()
class TestReadingListWithArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user, other_user):
        self.default_reading_list = ReadingListFactory(
            is_default=True, user=user, read_status=constants.ReadStatus.ONLY_UNREAD, order=0
        )
        self.reading_list = ReadingListFactory(
            user=user, order=10, enable_reading_on_scroll=True, auto_refresh_interval=60 * 60
        )
        self.default_reading_list_url = reverse("reading:default_reading_list")
        self.reading_list_url = reverse(
            "reading:reading_list", kwargs={"reading_list_slug": self.reading_list.slug}
        )

        self.read_article = ArticleFactory(
            read_at=utcnow(), published_at=datetime(2024, 3, 19, tzinfo=UTC), user=user
        )
        self.unread_article = ArticleFactory(
            read_at=None, published_at=datetime(2024, 3, 10, tzinfo=UTC), user=user
        )
        # Article of some other user.
        ArticleFactory(user=other_user)

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
        assert response.template_name == "feeds/list_of_articles.html"
        assert response.context["page_title"] == self.default_reading_list.name
        assert response.context["reading_lists"] == [self.default_reading_list, self.reading_list]
        assert response.context["displayed_reading_list_id"] == self.default_reading_list.id
        assert response.context["js_cfg"] == {
            "articles_list_min_refresh_timeout": 300,
            "auto_refresh_interval": 0,
            "is_reading_on_scroll_enabled": False,
        }
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [self.unread_article]

    def test_reading_list_view(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(10):
            response = logged_in_sync_client.get(self.reading_list_url)

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/list_of_articles.html"
        assert response.context["page_title"] == self.reading_list.name
        assert response.context["displayed_reading_list_id"] == self.reading_list.id
        assert response.context["reading_lists"] == [self.default_reading_list, self.reading_list]
        assert response.context["js_cfg"] == {
            "is_reading_on_scroll_enabled": True,
            "auto_refresh_interval": 60 * 60,
            "articles_list_min_refresh_timeout": 300,
        }
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [
            self.read_article,
            self.unread_article,
        ]
        assert response.context["from_url"] == self.reading_list_url

    def test_reading_list_view_with_htmx(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(10):
            response = logged_in_sync_client.get(
                self.reading_list_url,
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/partials/article_paginator_page.html"
        assert response.context["page_title"] == self.reading_list.name
        assert response.context["displayed_reading_list_id"] == self.reading_list.id
        assert response.context["reading_lists"] == [self.default_reading_list, self.reading_list]
        assert response.context["js_cfg"] == {
            "is_reading_on_scroll_enabled": True,
            "auto_refresh_interval": 60 * 60,
            "articles_list_min_refresh_timeout": 300,
        }
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [
            self.read_article,
            self.unread_article,
        ]
        assert response.context["from_url"] == self.reading_list_url

    def test_reading_list_view_with_htmx_full_reload(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(10):
            response = logged_in_sync_client.get(
                f"{self.reading_list_url}?full_reload=true",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "feeds/list_of_articles.html"
        assert response.context["page_title"] == self.reading_list.name
        assert response.context["displayed_reading_list_id"] == self.reading_list.id
        assert response.context["reading_lists"] == [self.default_reading_list, self.reading_list]
        assert response.context["js_cfg"] == {
            "is_reading_on_scroll_enabled": True,
            "auto_refresh_interval": 60 * 60,
            "articles_list_min_refresh_timeout": 300,
        }
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [
            self.read_article,
            self.unread_article,
        ]
        assert response.context["from_url"] == self.reading_list_url
        assert response["HX-Push-Url"] == self.reading_list_url


@pytest.mark.django_db()
class TestTagWithArticlesView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.tag_to_display = TagFactory(user=user)
        other_tag = TagFactory(user=user)
        self.url = reverse(
            "reading:tag_with_articles", kwargs={"tag_slug": self.tag_to_display.slug}
        )
        self.article_in_list = ArticleFactory(user=user)
        ArticleTag.objects.create(tag=self.tag_to_display, article=self.article_in_list)
        other_article = ArticleFactory(user=user)
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
        assert response.template_name == "feeds/list_of_articles.html"
        assert response.context["page_title"] == f"Articles with tag '{self.tag_to_display.name}'"
        assert response.context["displayed_reading_list_id"] is None
        assert response.context["reading_lists"] == []
        assert response.context["js_cfg"] == {}
        assert isinstance(response.context["articles_paginator"], Paginator)
        assert response.context["articles_page"].object_list == [
            self.article_in_list,
        ]
